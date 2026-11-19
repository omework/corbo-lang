"""Validate the emitted growth cursors against an interval model."""

import random
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from crust import compile_source


class GrowthRuntimeTests(unittest.TestCase):
    def test_local_cells_keep_layout_and_destroy_owned_pool_fields(self):
        emitted = compile_source('fn main() {}').replace('int main(void)', 'int crust_unused_main(void)')
        harness = r"""
#include <assert.h>
int main(int argc, char **argv) {
    Source stack = source_stack(4096);
    Source pool = source_pool(1);
    const size_t offsets[] = {0};
    const unsigned char owned[] = {2};
    Source point = {.enum_name = "Point", .arm_name = "", .field_count = 1,
                    .field_offsets = offsets};
    Source holder = {.enum_name = "Holder", .arm_name = "", .field_count = 1,
                     .field_offsets = offsets, .field_kinds = owned};
    if (argc > 1 && argv[1][0] == 'o') local_cell_new(&stack, &point, SIZE_MAX, NULL);
    if (argc > 1 && argv[1][0] == 'p') local_cell_new(&pool, &point, 0, NULL);
    Cell *parent = local_cell_new(&stack, &point, sizeof(int), NULL);
    cell_store_int(parent, 0, 42);
    size_t boundary = stack.used;
    Cell *child = cell_new(&pool, 7, NULL);
    Cell *owner = local_cell_new(&stack, &holder, sizeof(Cell *), NULL);
    cell_store_ref(owner, 0, child);
    Cell *temporary = local_cell_new(&stack, &point, 256, NULL);
    cell_store_int(temporary, 0, 99);
    cell_drop(owner);
    assert(pool.live == 0 && pool.used == 0);
    assert(stack.used > boundary && stack.live == 2);
    assert(cell_load_int(parent, 0) == 42 && cell_load_int(temporary, 0) == 99);
    cell_drop(temporary);
    assert(stack.used == boundary && stack.tail == parent);
    Cell *again = local_cell_new(&stack, &point, sizeof(int), NULL);
    assert(again == owner && again->layout == &point);
    cell_store_int(again, 0, 12);
    cell_drop(again);
    assert(pool.live == 0 && stack.used == boundary);
    cell_drop(parent);
    assert(stack.used == 0);
    source_close(&pool);
    source_close(&stack);
    return 0;
}
"""
        self.native(emitted + harness, (([], ''),
                    (['overflow'], 'local value layout too large\n'),
                    (['pool'], 'local value requires a data stack\n')))

    def test_mixed_size_stack_cells_against_interval_model(self):
        rng = random.Random(9081)
        intervals = []
        live = {}
        code = []
        cursor = 0
        for step in range(200):
            if live and rng.randrange(3) == 0:
                handle = rng.choice(list(live))
                del live[handle]
                code.append(f'cell_drop(cells[{handle}]);')
                while intervals and intervals[-1][0] not in live:
                    _, cursor, _ = intervals.pop()
            else:
                units = rng.randrange(1, 7)
                end = cursor + units
                code.append(f'cells[{step}] = cell_try_new_sized_unlocked(&stack, '
                            f'{units} * sizeof(Cell), 0, NULL);')
                if end > 47:
                    code.append(f'assert(cells[{step}] == NULL);')
                else:
                    code.append(f'assert((unsigned char *)cells[{step}] == '
                                f'stack.base + {cursor} * sizeof(Cell));')
                    intervals.append((step, cursor, end))
                    live[step] = (cursor, end)
                    cursor = end
                    code.append(f'cells[{step}]->value = {step};')
            code.append(f'assert(stack.used == {cursor} * sizeof(Cell));')
            code.append(f'assert(stack.live == {len(live)});')
            for handle in live:
                code.append(f'assert(cells[{handle}]->value == {handle});')
        code.extend(f'cell_drop(cells[{handle}]);' for handle in live)
        emitted = compile_source('fn main() {}').replace('int main(void)', 'int crust_unused_main(void)')
        harness = ('\n#include <assert.h>\nint main(void) {\n'
                   'Source stack = source_stack(47 * sizeof(Cell));\n'
                   'Cell *cells[200] = {0};\n' + '\n'.join(code) +
                   '\nassert(stack.used == 0 && stack.live == 0);\n'
                   'source_close(&stack); return 0; }\n')
        self.native(emitted + harness, (([], ''),))

    def test_two_fronts_against_interval_model(self):
        rng = random.Random(2219)
        capacity = 63
        # Keep allocated intervals per side, independently of C's cursor state.
        live = [None, None]
        code = []

        def check():
            for span in live:
                if span is not None:
                    for start, block in span[1]:
                        if block:
                            values = ", ".join(map(str, block))
                            code.append(f"assert(memcmp(stack.mapping.base + {start}, "
                                        f"(const unsigned char[]){{{values}}}, {len(block)}) == 0);")

        for _ in range(180):
            side = rng.randrange(2)
            peer = live[1 - side]
            if peer is None:
                peer_edge = capacity if side == 0 else 0
            else:
                start, block = peer[1][-1]
                peer_edge = start if side == 0 else start + len(block)
            span = live[side]
            if span is None:
                width = rng.choice((1, 2, 4, 8))
                boundary = 0 if side == 0 else capacity - capacity % width
                fits = boundary <= peer_edge if side == 0 else boundary >= peer_edge
                code.append(f"assert(growth_open(&stack, &spans[{side}], {side}, {width}, {width}) == {int(fits)});")
                if fits:
                    live[side] = (width, [(boundary, b"")])
            elif rng.randrange(4) == 0:
                code.append(f"growth_release(&spans[{side}]);")
                live[side] = None
            else:
                width, blocks = span
                count = rng.randrange(0, 12)
                previous, last = blocks[-1]
                size = count * width
                start = previous + len(last) if side == 0 else previous - size
                fits = start + size <= peer_edge if side == 0 else start >= peer_edge
                code.append(f"p = growth_extend(&spans[{side}], {count});")
                if fits:
                    code.append(f"assert(p == stack.mapping.base + {start});")
                    data = bytes(rng.randrange(1, 256) for _ in range(size))
                    if data:
                        code.append("memcpy(p, (const unsigned char[]){" + ", ".join(map(str, data)) + f"}}, {size});")
                    blocks.append((start, data))
                else:
                    code.append("assert(p == NULL);")
            check()
        for side, span in enumerate(live):
            if span is not None:
                code.append(f"growth_release(&spans[{side}]);")

        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(int argc, char **argv) {
    GrowthStack stack = growth_stack(63);
    GrowthSpan spans[2] = {0}, extra = {0};
    unsigned char *p;
    if (argc > 1) {
        assert(growth_open(&stack, &spans[0], GROWTH_LOW, 1, 1));
        if (strcmp(argv[1], "close") == 0) growth_close(&stack);
        GrowthSpan copy = spans[0];
        assert(growth_extend(&copy, 1) == NULL);
        growth_release(&copy);
        return 0;
    }
    assert(!growth_open(&stack, &extra, GROWTH_LOW, 3, 2));
    assert(!growth_open(&stack, &extra, GROWTH_LOW, 1, 0));
    assert(growth_open(&stack, &spans[0], GROWTH_LOW, 1, 1));
    assert(!growth_open(&stack, &extra, GROWTH_LOW, 1, 1));
    assert(growth_open(&stack, &spans[1], GROWTH_HIGH, 1, 1));
    assert(growth_extend(&spans[0], 31) == stack.mapping.base);
    assert(growth_extend(&spans[1], 32) == stack.mapping.base + 31);
    assert(growth_extend(&spans[0], 1) == NULL);
    assert(growth_extend(&spans[1], SIZE_MAX) == NULL);
    growth_release(&spans[0]);
    assert(growth_extend(&spans[1], 31) == stack.mapping.base);
    growth_release(&spans[1]);
""" + "\n".join(code) + """
    assert(stack.low == 0 && stack.high == 63);
    growth_close(&stack);
    assert(!growth_open(&stack, &extra, GROWTH_LOW, 1, 1));
    return 0;
}
"""
        self.native(emitted + harness, (
            ([], ""),
            (["close"], "data stack avec un front encore vivant\n"),
            (["copy"], "front de croissance inactif\n"),
        ))

    def native(self, code, executions):
        compiler = shutil.which("clang") or shutil.which("cc")
        if compiler is None:
            self.skipTest("C compiler unavailable")

        with tempfile.TemporaryDirectory() as folder:
            c_path = Path(folder) / "growth.c"
            executable = Path(folder) / "growth"
            c_path.write_text(code)
            for opt in ("-O0", "-O2"):
                with self.subTest(opt=opt):
                    build = subprocess.run(
                        [compiler, "-std=c11", opt, "-fsanitize=undefined",
                         "-fno-sanitize-recover=all",
                         *(["-pthread"] if code.startswith("#define CRUST_THREAD_RUNTIME") else []),
                         str(c_path), "-o", str(executable)],
                        capture_output=True, text=True, timeout=30,
                    )
                    self.assertEqual(build.returncode, 0, build.stderr)
                    for args, expected in executions:
                        result = subprocess.run([str(executable), *args], capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, int(bool(expected)), result.stderr)
                        self.assertEqual(result.stderr, expected)

    def test_regions_reuse_holes_and_rewind_suffix_against_model(self):
        rng = random.Random(6077)
        capacity, region_size = 4, 37
        slots, holes = [], []
        live = {}
        code = []
        for _ in range(220):
            handle = rng.randrange(capacity + 1)
            if handle not in live:
                width = rng.choice((1, 2, 4, 8))
                code.append(f"opened = growth_region_open(&pool, &regions[{handle}], {width}, {width});")
                if len(slots) < capacity:
                    slot = len(slots)
                    slots.append(handle)
                elif holes:
                    slot = holes.pop()
                    slots[slot] = handle
                else:
                    code.append("assert(!opened);")
                    continue
                live[handle] = (slot, width, b"")
                code.append(f"assert(opened && (unsigned char *)regions[{handle}].slot == "
                            f"pool.slots.base + {slot} * pool.slots.stride);")
            elif rng.randrange(3) == 0:
                slot, _, _ = live.pop(handle)
                slots[slot] = None
                holes.append(slot)
                while slots and slots[-1] is None:
                    holes.remove(len(slots) - 1)
                    slots.pop()
                code.append(f"growth_region_release(&regions[{handle}]);")
            else:
                slot, width, old = live[handle]
                count = rng.randrange(12)
                code.append(f"p = growth_region_extend(&regions[{handle}], {count});")
                if len(old) + width * count > region_size:
                    code.append("assert(!p);")
                else:
                    data = bytes(rng.randrange(1, 256) for _ in range(width * count))
                    code.append(f"assert(p == payload(&pool, {slot}) + {len(old)} && (uintptr_t)p % {width} == 0);")
                    if data:
                        values = ", ".join(map(str, data))
                        code.append(f"memcpy(p, (const unsigned char[]){{{values}}}, {len(data)});")
                    live[handle] = (slot, width, old + data)
            code.append(f"assert(pool.slots.used == {len(slots)} * pool.slots.stride);")
            for slot, _, data in live.values():
                if data:
                    values = ", ".join(map(str, data))
                    code.append(f"assert(memcmp(payload(&pool, {slot}), "
                                f"(const unsigned char[]){{{values}}}, {len(data)}) == 0);")
        for handle in live:
            code.append(f"growth_region_release(&regions[{handle}]);")

        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
static unsigned char *payload(GrowthRegionPool *pool, size_t slot) {
    return pool->slots.base + slot * pool->slots.stride + pool->payload_offset;
}
int main(int argc, char **argv) {
    GrowthRegionPool pool = growth_region_pool(4, 37);
    GrowthRegion regions[5] = {0};
    int opened;
    unsigned char *p;
    assert(growth_region_open(&pool, &regions[0], 1, 1));
    if (argc > 1 && strcmp(argv[1], "close") == 0) growth_region_pool_close(&pool);
    GrowthRegion copy = regions[0];
    assert(growth_region_extend(&copy, 1) == NULL);
    if (argc > 1) growth_region_release(&copy);
    assert(growth_region_extend(&regions[0], 37) == payload(&pool, 0));
    assert(growth_region_extend(&regions[0], 1) == NULL);
    assert(growth_region_extend(&regions[0], SIZE_MAX) == NULL);
    growth_region_release(&regions[0]);
    assert(growth_region_open(&pool, &regions[1], 1, 1));
    assert(growth_region_extend(&copy, 1) == NULL);
    growth_region_release(&regions[1]);
""" + "\n".join(code) + """
    assert(pool.slots.used == 0 && pool.slots.free_head == NULL);
    growth_region_pool_close(&pool);
    assert(growth_region_extend(&copy, 1) == NULL);
    assert(!growth_region_open(&pool, &regions[0], 1, 1));
    return 0;
}
"""
        self.native(emitted + harness, (
            ([], ""),
            (["close"], "internal error: source still has live allocations\n"),
            (["copy"], "région de croissance inactive\n"),
        ))

    def test_placement_falls_back_without_changing_limits_or_live_addresses(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    GrowthStack stack = growth_stack(24);
    GrowthSpanPlacement low = {0}, high = {0}, fallback = {0}, retry = {0};
    assert(growth_place(&low, &stack, 64, 8, 8));
    assert(low.span.stack == &stack && low.span.front == GROWTH_LOW);
    assert(growth_extend(&low.span, 2) == stack.mapping.base);
    assert(growth_place(&high, &stack, 64, 8, 8));
    assert(high.span.stack == &stack && high.span.front == GROWTH_HIGH);
    unsigned char *last = growth_extend(&high.span, 1);
    assert(last == stack.mapping.base + 16);
    *last = 21;
    assert(!growth_extend(&high.span, 1));
    assert(!growth_place(&retry, &stack, 4, 8, 8));
    assert(growth_place(&fallback, &stack, 64, 8, 8));
    assert(fallback.span.stack == &fallback.dedicated);
    assert(growth_extend(&fallback.span, 8) == fallback.dedicated.mapping.base);
    assert(!growth_extend(&fallback.span, 1));
    growth_unplace(&fallback);
    assert(!fallback.dedicated.mapping.capacity && *last == 21);
    growth_unplace(&low);
    assert(*last == 21);
    growth_unplace(&high);
    growth_close(&stack);

    GrowthRegionPool pool = growth_region_pool(1, 12);
    GrowthRegionPlacement first = {0}, full = {0}, other = {0};
    assert(!growth_region_place(&first, &pool, 12, 4, 3));
    assert(growth_region_place(&first, &pool, 12, 4, 4));
    unsigned char *data = growth_region_extend(&first.region, 3);
    assert(data && first.region.pool == &pool);
    *data = 42;
    assert(growth_region_place(&full, &pool, 12, 4, 4));
    assert(full.region.pool == &full.dedicated && full.dedicated.region_size == 12);
    assert(growth_region_extend(&full.region, 3));
    assert(!growth_region_extend(&full.region, 1));
    growth_region_unplace(&full);
    growth_region_unplace(&first);
    assert(growth_region_place(&other, &pool, 20, 4, 4));
    assert(other.region.pool == &other.dedicated && pool.slots.live == 0);
    assert(growth_region_extend(&other.region, 5));
    assert(!growth_region_extend(&other.region, 1));
    growth_region_unplace(&other);
    assert(growth_region_place(&first, &pool, 12, 4, 4));
    assert(growth_region_extend(&first.region, 1) == data);
    growth_region_unplace(&first);
    growth_region_pool_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_string_contents_stay_in_place_and_cleanup_releases_region(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(int argc, char **argv) {
    (void)argv;
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    Cell *a = string_new(&pool, 6, NULL);
    Cell *b = string_new(&pool, 5, NULL);
    assert(string_byte_len(a) == 0 && string_byte_len(b) == 0);
    GrowthRegionPool *class_a = vector_items(a)->region.region.pool;
    GrowthRegionPool *class_b = vector_items(b)->region.region.pool;
    assert(class_a != class_b && storage.class_count == 2);
    assert(class_a->region_size == 6 && class_b->region_size == 5);
    assert(class_b->slots.base >= storage.stack.mapping.base);
    assert(class_b->slots.base + class_b->slots.capacity <= class_a->slots.base);
    assert(class_a->slots.base + class_a->slots.capacity ==
           storage.stack.mapping.base + storage.stack.mapping.capacity);
    assert(!vector_items(a)->region.dedicated.region_size && !vector_items(b)->region.dedicated.region_size);
    const unsigned char sample[] = {0xc3, 0xa9};
    const unsigned char rest[] = {0xf0, 0x9f, 0x8c, 0x8d};
    unsigned char *secondary_origin = growth_region_extend(&vector_items(b)->region.region, 0);
    cell_drop(b);
    b = string_new(&pool, 5, NULL);
    assert(vector_items(b)->region.region.pool == class_b);
    string_push_str(b, (CrustText){sample, sizeof sample});
    assert(string_view(b).bytes == secondary_origin);
    unsigned char *origin = growth_region_extend(&vector_items(a)->region.region, 0);
    string_push_str(a, (CrustText){sample, sizeof sample});
    string_push(a, UINT32_C(0x1f30d));
    assert(string_byte_len(a) == 6);
    assert(growth_region_extend(&vector_items(a)->region.region, 0) == origin + 6);
    CrustText view = string_view(a);
    assert(view.bytes == origin && view.length == 6);
    assert(memcmp(origin, sample, 2) == 0 && memcmp(origin + 2, rest, 4) == 0);
    if (argc > 1) string_push(a, UINT32_C(0x1f30d));
    cell_drop(a);
    Cell *reused = string_new(&pool, 6, NULL);
    assert(reused == a && string_byte_len(reused) == 0);
    assert(growth_region_extend(&vector_items(reused)->region.region, 0) == origin);
    cell_drop(reused);
    Cell *changed = string_new(&pool, 9, NULL);
    assert(vector_items(changed)->region.region.pool == class_a);
    assert(class_a->region_size == 9 && class_b->region_size == 5);
    assert(storage.class_count == 2);
    assert(string_view(b).bytes == secondary_origin && string_byte_len(b) == 2);
    assert(memcmp(secondary_origin, sample, sizeof sample) == 0);
    cell_drop(changed);
    cell_drop(b);
    assert(class_a->slots.used == 0 && class_b->slots.used == 0);
    source_close(&pool);
    assert(!storage.region_classes.base && !storage.stack.mapping.base && storage.class_count == 0);
    pool = source_vector_pool(3, &storage);
    a = string_new(&pool, 2 * 1024 * 1024, NULL);
    b = string_new(&pool, 1024 * 1024, NULL);
    Cell *overflow = string_new(&pool, 1024 * 1024, NULL);
    assert(!vector_items(a)->region.dedicated.region_size && !vector_items(b)->region.dedicated.region_size);
    assert(vector_items(overflow)->region.dedicated.region_size == 1024 * 1024);
    assert(storage.class_count == 2);
    cell_drop(overflow);
    cell_drop(b);
    cell_drop(a);
    source_close(&pool);
    pool = source_vector_pool(3, &storage);
    a = string_new(&pool, 0, NULL);
    b = string_new(&pool, 0, NULL);
    Cell *dedicated = string_new(&pool, 0, NULL);
    assert(vector_items(a)->span.span.stack == &storage.stack);
    assert(vector_items(a)->span.span.front == GROWTH_LOW);
    assert(vector_items(b)->span.span.stack == &vector_items(b)->span.dedicated);
    assert(vector_items(b)->span.span.front == GROWTH_LOW);
    assert(vector_items(dedicated)->span.span.stack == &vector_items(dedicated)->span.dedicated);
    string_push_str(a, (CrustText){sample, sizeof sample});
    string_push_str(b, (CrustText){sample, sizeof sample});
    view = string_view(b);
    assert(!view.descends && view.length == sizeof sample);
    const unsigned char *first_byte = text_address(view, 0);
    string_push(b, UINT32_C(0x1f30d));
    view = string_view(b);
    assert(text_address(view, 0) == first_byte);
    for (size_t i = 0; i < sizeof sample; ++i)
        assert(*text_address(view, i) == sample[i]);
    for (size_t i = 0; i < sizeof rest; ++i)
        assert(*text_address(view, sizeof sample + i) == rest[i]);
    assert(string_view(a).length == sizeof sample);
    cell_drop(dedicated);
    cell_drop(b);
    cell_drop(a);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""), (["overflow"], "capacité de String dépassée\n")))

    def test_string_pop_matches_scalar_stack_and_reclaims_capacity(self):
        rng = random.Random(9407)
        code = []
        values = []
        used = 0
        alphabet = ("a", "é", "€", "🌍", "\0", "\u0301")
        for _ in range(120):
            char = rng.choice(alphabet)
            width = len(char.encode("utf-8"))
            if used + width <= 12 and rng.randrange(3) != 0:
                values.append(char)
                used += width
                code.append(f"string_push(s, {ord(char)});")
            else:
                code.append("popped = string_pop(s);")
                if values:
                    char = values.pop()
                    used -= len(char.encode("utf-8"))
                    code.append(f"assert(popped.status == CRUST_CHAR_OK && popped.value == {ord(char)});")
                else:
                    code.append("assert(popped.status == CRUST_CHAR_NONE);")
            code.append(f"assert(string_view(s).length == {used} && string_view(s).bytes == origin);")
            data = "".join(values).encode("utf-8")
            if data:
                code.append("assert(memcmp(origin, (const unsigned char[]){"
                            + ", ".join(map(str, data)) + f"}}, {len(data)}) == 0);")

        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
static void exercise(uint64_t limit) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(1, &storage);
    Cell *s = string_new(&pool, limit, NULL);
    const unsigned char *origin = string_view(s).bytes;
    CrustCharResult popped;
""" + "\n".join(code) + """
    cell_drop(s);
    source_close(&pool);
}
int main(void) {
    exercise(12);
    exercise(0);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_string_byte_replacement_agrees_with_utf8_model(self):
        rng = random.Random(3581)
        current = "été🌍ab".encode()
        initial = ", ".join(map(str, current))
        code = []
        cases = [(0, b"ab"), (2, b"\xff"), (len(current), b"")]
        cases.extend((rng.randrange(-1, len(current) + 2),
                      bytes(rng.randrange(256) for _ in range(rng.randrange(5))))
                     for _ in range(180))
        for index, (start, data) in enumerate(cases):
            if index % 2 == 0:
                replacement = ", ".join(map(str, data[::-1] or b"\0"))
                code.append(f"result = string_replace_slice(s, {start}, "
                            f"(VectorSlice){{(const unsigned char[]){{{replacement}}}, {len(data)}, 1}});")
            elif len(data) == 1:
                code.append(f"result = string_replace_byte(s, {start}, {data[0]});")
            else:
                replacement = ", ".join(map(str, data or b"\0"))
                code.append(f"result = string_replace_bytes(s, {start}, "
                            f"(const unsigned char[]){{{replacement}}}, {len(data)});")
            if start < 0 or start + len(data) > len(current):
                expected = 7
            else:
                changed = current[:start] + data + current[start + len(data):]
                try:
                    changed.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    expected = 8
                else:
                    expected = 0
                    if len(data) == 1:
                        code.append(f"assert(result.value == {current[start]});")
                    current = changed
            code.append(f"assert(result.status == {expected});")
            expected_data = ", ".join(map(str, current))
            code.append(f"assert(string_view(s).bytes == origin && string_view(s).length == {len(current)});")
            code.append(f"for (size_t j = 0; j < {len(current)}; ++j) "
                        f"assert(*text_address(string_view(s), j) == ((const unsigned char[]){{{expected_data}}})[j]);")

        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = f"""
#include <assert.h>
static void check_replacements(int descending) {{
    VectorStorage storage = {{0}};
    Source pool = source_vector_pool(2, &storage);
    Cell *first = descending ? string_new(&pool, 0, NULL) : NULL;
    Cell *s = descending ? vector_new(&pool, 0, 1, 1, 0, NULL) : string_new(&pool, 32, NULL);
    assert(string_view(s).descends == descending);
    static const unsigned char data[] = {{{initial}}};
    string_push_str(s, (CrustText){{data, sizeof data}});
    const unsigned char *origin = string_view(s).bytes;
    CrustByteResult result;
""" + "\n".join(code) + """
    const unsigned char *first_byte = text_address(string_view(s), 0);
    string_push(s, UINT32_C(0x1f30d));
    assert(text_address(string_view(s), 0) == first_byte);
    CrustCharResult popped = string_pop(s);
    assert(popped.status == CRUST_CHAR_OK && popped.value == UINT32_C(0x1f30d));
    assert(text_address(string_view(s), 0) == first_byte);
    cell_drop(s);
    if (first) cell_drop(first);
    source_close(&pool);
}
int main(void) {
    check_replacements(0);
    check_replacements(1);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_vector_try_growth_leaves_prefix_and_cursor_on_failure(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    storage.stack = growth_stack(4);
    Cell *left = vector_new(&pool, 0, 1, 1, 0, NULL);
    Cell *right = vector_new(&pool, 0, 1, 1, 0, NULL);
    assert(vector_try_push(left, (const uint8_t[]){5}) == CRUST_VECTOR_OK);
    const uint8_t block[] = {7, 8};
    assert(vector_try_extend_bytes(right, block, 2).status == CRUST_VECTOR_OK);
    size_t high = storage.stack.high;
    assert(vector_try_extend_bytes(right, block, 2).status == CRUST_VECTOR_CAPACITY);
    VectorItems *items = vector_items(right);
    assert(storage.stack.high == high && items->length == 2);
    assert(*vector_item_at(items, 0) == 7 && *vector_item_at(items, 1) == 8);
    assert(vector_try_push(right, (const uint8_t[]){9}) == CRUST_VECTOR_OK);
    uint8_t incoming = 200;
    assert(vector_try_push(right, &incoming) == CRUST_VECTOR_REJECTED);
    assert(incoming == 200 && items->length == 3 && *vector_item_at(items, 2) == 9);
    cell_drop(right);
    cell_drop(left);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_vector_equality_reads_opposite_fronts_in_logical_order(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>

int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    storage.stack = growth_stack(8 * sizeof(int));
    Cell *low = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    Cell *high = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    assert(!vector_descends(vector_items(low)) && vector_descends(vector_items(high)));
    assert(vector_values_equal(low, high));
    const int first = -7, second = 19;
    vector_push(low, &first);
    assert(!vector_values_equal(low, high));
    vector_push(high, &first);
    vector_push(low, &second);
    vector_push(high, &second);
    assert(vector_values_equal(low, high));
    int replacement = second;
    assert(vector_replace(high, 0, &replacement) == CRUST_VECTOR_OK);
    replacement = first;
    assert(vector_replace(high, 1, &replacement) == CRUST_VECTOR_OK);
    assert(!vector_values_equal(low, high));
    cell_drop(high);
    cell_drop(low);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_vector_handle_cells_reclaim_their_original_pools(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>

int main(void) {
    Source p = source_pool(2), q = source_pool(2);
    VectorStorage storage = {0};
    Source vectors = source_vector_pool(2, &storage);
    storage.stack = growth_stack(3 * sizeof(Cell *));
    Cell *low = vector_new_handles(&vectors, 0, NULL);
    Cell *high = vector_new_handles(&vectors, 0, NULL);
    assert(!vector_descends(vector_items(low)) && vector_descends(vector_items(high)));

    Cell *a = cell_new(&p, 10, NULL), *b = cell_new(&q, 20, NULL);
    Cell *c = cell_new(&p, 30, NULL), *d = cell_new(&q, 40, NULL);
    assert(vector_try_push(high, &a) == CRUST_VECTOR_OK);
    unsigned char *high_slot = vector_item_at(vector_items(high), 0);
    assert(vector_try_push(high, &b) == CRUST_VECTOR_OK);
    assert(vector_try_push(high, &c) == CRUST_VECTOR_OK);
    assert(vector_try_push(high, &d) == CRUST_VECTOR_REJECTED);
    assert(d->alive && d->source == &q && d->value == 40);

    Cell *result = d;
    assert(vector_replace(high, 3, &result) == CRUST_VECTOR_REJECTED && result == d);
    assert(vector_replace(high, 1, &result) == CRUST_VECTOR_OK && result == b);
    assert(b->source == &q && b->value == 20);
    cell_drop(b);

    vector_remove(high, 0, &result);
    assert(result == a && a->source == &p && a->value == 10);
    assert(vector_pop(high, &result) == CRUST_CHAR_OK && result == c);
    assert(c->source == &p && c->value == 30);
    vector_read(high, 0, &result);
    assert(result == d);

    vector_push(low, &a);
    unsigned char *low_slot = vector_item_at(vector_items(low), 0);
    size_t low_cursor = storage.stack.low;
    cell_drop(high);
    assert(q.live == 0 && p.live == 2);
    assert(storage.stack.high == storage.stack.mapping.capacity);
    assert(storage.stack.low == low_cursor && vector_item_at(vector_items(low), 0) == low_slot);
    Cell *reused_q = cell_new(&q, 50, NULL);
    assert(reused_q == b);
    high = vector_new_handles(&vectors, 0, NULL);
    vector_push(high, &reused_q);
    assert(vector_item_at(vector_items(high), 0) == high_slot);
    cell_drop(high);
    assert(q.live == 0 && storage.stack.high == storage.stack.mapping.capacity);
    cell_drop(low);
    assert(p.live == 1 && c->alive && storage.stack.low == 0);
    Cell *reused_p = cell_new(&p, 60, NULL);
    assert(reused_p == a);
    cell_drop(reused_p);
    cell_drop(c);
    source_close(&vectors);
    vectors = source_vector_pool(2, &storage);
    Cell *region = vector_new_handles(&vectors, 2 * sizeof(Cell *), NULL);
    assert(!vector_items(region)->region.dedicated.region_size);
    a = cell_new(&p, 70, NULL);
    b = cell_new(&q, 80, NULL);
    vector_push(region, &a);
    vector_push(region, &b);
    unsigned char *region_slot = vector_item_at(vector_items(region), 0);
    cell_drop(region);
    assert(p.live == 0 && q.live == 0);
    region = vector_new_handles(&vectors, 2 * sizeof(Cell *), NULL);
    reused_p = cell_new(&p, 90, NULL);
    vector_push(region, &reused_p);
    assert(vector_item_at(vector_items(region), 0) == region_slot);
    cell_drop(region);
    source_close(&vectors);
    source_close(&q);
    source_close(&p);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_vector_external_read_distinguishes_short_eof_full_and_error(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>

static int input(const unsigned char *bytes, size_t count) {
    int ends[2];
    assert(pipe(ends) == 0);
    assert(write(ends[1], bytes, count) == (ssize_t)count);
    assert(close(ends[1]) == 0);
    return ends[0];
}

static void content(Cell *cell, const unsigned char *expected, size_t length) {
    assert(vector_items(cell)->length == length);
    for (size_t i = 0; i < length; ++i) {
        uint8_t byte;
        vector_read(cell, (int)i, &byte);
        assert(byte == expected[i]);
    }
}

int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(3, &storage);
    storage.stack = growth_stack(9);
    Cell *left = vector_new(&pool, 0, 1, 1, 0, NULL);
    Cell *right = vector_new(&pool, 0, 1, 1, 0, NULL);
    Cell *region = vector_new(&pool, 3, 1, 1, 0, NULL);
    assert(vector_descends(vector_items(right)));
    vector_push(left, "L");
    vector_push(right, "R");

    int fd = input((const unsigned char *)"abc", 3);
    VectorReadResult result = vector_read_fd(right, fd);
    assert(result.status == VECTOR_READ_DATA && result.count == 3);
    content(right, (const unsigned char *)"Rabc", 4);
    size_t high = storage.stack.high;
    assert(vector_read_fd(right, fd).status == VECTOR_READ_EOF);
    assert(close(fd) == 0);
    result = vector_read_fd(right, -1);
    assert(result.status == VECTOR_READ_ERROR && result.count == 0 && result.error == EBADF);
    assert(storage.stack.high == high);
    content(right, (const unsigned char *)"Rabc", 4);

    fd = input((const unsigned char *)"defgh", 5);
    result = vector_read_fd(left, fd);
    assert(result.status == VECTOR_READ_DATA && result.count == 4);
    assert(vector_read_fd(left, fd).status == VECTOR_READ_FULL);
    content(left, (const unsigned char *)"Ldefg", 5);
    content(right, (const unsigned char *)"Rabc", 4);

    result = vector_read_fd(region, fd);
    assert(result.status == VECTOR_READ_DATA && result.count == 1);
    assert(vector_read_fd(region, fd).status == VECTOR_READ_EOF);
    content(region, (const unsigned char *)"h", 1);
    assert(close(fd) == 0);

    cell_drop(region);
    cell_drop(right);
    cell_drop(left);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_vector_split_ranges_are_disjoint_at_every_boundary(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>

static void check_split(Cell *cell, size_t length, size_t element_size) {
    VectorItems *items = vector_items(cell);
    assert(items->length == length);
    for (size_t middle = 0; middle <= length; ++middle) {
        VectorSplit split = vector_split_at_mut(cell, (int)middle);
        assert(split.left.length == middle && split.right.length == length - middle);
        assert((split.left.base == NULL) == (middle == 0));
        assert((split.right.base == NULL) == (middle == length));
        for (size_t j = 0; j < middle; ++j) {
            const unsigned char *left = vector_slice_address(split.left, (int)j, element_size);
            assert(left == vector_item_at(items, j));
            for (size_t k = 0; k < split.right.length; ++k)
                assert(left != vector_slice_address(split.right, (int)k, element_size));
        }
        for (size_t j = 0; j < split.right.length; ++j)
            assert(vector_slice_address(split.right, (int)j, element_size) ==
                   vector_item_at(items, middle + j));
    }
}

int main(int argc, char **argv) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    Cell *low = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    Cell *high = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    assert(!vector_descends(vector_items(low)) && vector_descends(vector_items(high)));
    check_split(low, 0, sizeof(int));
    check_split(high, 0, sizeof(int));
    const int values[] = {2, 3, 5, 7, 11};
    assert(vector_try_extend(vector_items(low), values, 5));
    assert(vector_try_extend(vector_items(high), values, 5));
    if (argc > 1) vector_split_at_mut(high, argv[1][0] == '-' ? -1 : 6);
    check_split(low, 5, sizeof(int));
    check_split(high, 5, sizeof(int));
    VectorSplit split = vector_split_at_mut(high, 2);
    *(int *)vector_slice_address(split.left, 1, sizeof(int)) = -3;
    *(int *)vector_slice_address(split.right, 0, sizeof(int)) = -5;
    const int expected[] = {2, -3, -5, 7, 11};
    for (int i = 0; i < 5; ++i) {
        int value;
        vector_read(high, i, &value);
        assert(value == expected[i]);
        vector_read(low, i, &value);
        assert(value == values[i]);
    }
    VectorStorage region_storage = {0};
    Source region_pool = source_vector_pool(1, &region_storage);
    Cell *region = vector_new(&region_pool, 5, sizeof(uint8_t), _Alignof(uint8_t), 0, NULL);
    const uint8_t bytes[] = {10, 20, 30, 40, 50};
    assert(vector_try_extend(vector_items(region), bytes, 5));
    check_split(region, 5, sizeof(uint8_t));
    cell_drop(region);
    source_close(&region_pool);
    cell_drop(high);
    cell_drop(low);
    source_close(&pool);
    return 0;
}
"""
        error = "indice de séparation de Vector hors limites\n"
        self.native(emitted + harness, (([], ""), (["-1"], error), (["6"], error)))

    def test_vector_slices_preserve_order_across_physical_directions(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    storage.stack = growth_stack(16);
    Cell *left = vector_new(&pool, 0, 1, 1, 0, NULL);
    Cell *right = vector_new(&pool, 0, 1, 1, 0, NULL);
    VectorItems *a = vector_items(left), *b = vector_items(right);
    assert(vector_try_extend(a, (const uint8_t[]){1, 2, 3, 4}, 4));
    assert(vector_try_extend(b, (const uint8_t[]){5, 6, 7, 8}, 4));
    VectorSlice descending = vector_slice(right, 1, 3, 1);
    VectorSlice ascending = vector_slice(left, 1, 3, 1);
    assert(vector_slice_byte_address(descending, 0) == vector_item_at(b, 1));
    assert(vector_slice_byte_address(descending, 1) == vector_item_at(b, 2));
    assert(vector_slice_byte_address(ascending, 0) == vector_item_at(a, 1));
    assert(vector_slice_byte_address(ascending, 1) == vector_item_at(a, 2));
    assert(vector_try_extend_slice(left, vector_slice(right, 1, 3, 1)).status == CRUST_VECTOR_OK);
    assert(a->length == 6 && *vector_item_at(a, 4) == 6 && *vector_item_at(a, 5) == 7);
    assert(vector_try_extend_slice(right, vector_slice(left, 2, 0, 0)).status == CRUST_VECTOR_OK);
    assert(b->length == 8);
    const uint8_t expected[] = {5, 6, 7, 8, 3, 4, 6, 7};
    for (size_t i = 0; i < sizeof expected; ++i) assert(*vector_item_at(b, i) == expected[i]);
    assert(vector_try_extend_slice(right, vector_slice(left, 6, 6, 1)).status == CRUST_VECTOR_OK);
    assert(vector_try_extend_slice(right, vector_slice(left, 0, 3, 1)).status == CRUST_VECTOR_CAPACITY);
    assert(b->length == 8 && *vector_item_at(b, 7) == 7);
    cell_drop(right);
    cell_drop(left);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_cold_region_reservation_rolls_back_failed_mappings(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        emitted = emitted.replace("void *mapping = mmap(", "void *mapping = test_mmap(")
        emitted = emitted.replace("munmap(", "test_munmap(")
        emitted = emitted.replace("static const char *source_stack_mapping(", """
static int maps_until_failure, unmaps;
static void *test_mmap(void *address, size_t size, int protection, int flags, int fd, off_t offset) {
    if (maps_until_failure > 0 && --maps_until_failure == 0) return MAP_FAILED;
    return mmap(address, size, protection, flags, fd, offset);
}
static int test_munmap(void *address, size_t size) {
    ++unmaps;
    return munmap(address, size);
}
static const char *source_stack_mapping(""")
        harness = """
#include <assert.h>
int main(void) {
    for (int failure = 0; failure <= 2; ++failure) {
        VectorStorage storage = {0};
        Source pool = source_vector_pool(2, &storage);
        Cell *reserved = cell_reserve_for_transfer(&pool, 1);
        assert(reserved);
        maps_until_failure = failure;
        int before = unmaps;
        int early = vector_reserve_region(reserved, 32, 1, 1, 1, 1);
        assert(early == !failure);
        if (failure) {
            assert(unmaps - before == (failure == 2));
            assert(!storage.stack.mapping.base && !storage.region_classes.base);
        }
        Cell *temp = string_new(&pool, 32, NULL);
        Cell *value = vector_construct_reserved(reserved, early, &pool, 32, 1, 1, 1, 0, NULL);
        assert(value == reserved);
        unsigned char *a = vector_base(vector_items(value));
        unsigned char *b = vector_base(vector_items(temp));
        assert(early ? a < b : b < a);
        cell_drop(temp);
        string_push_str(value, (CrustText){(const unsigned char *)"ok", 2});
        assert(string_view(value).bytes == a && string_byte_len(value) == 2);
        cell_drop(value);
        source_close(&pool);
    }
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_annotated_region_can_be_reserved_before_temporary_payload(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(3, &storage);
    Cell *warm = string_new(&pool, 32, NULL);
    Cell *reserved = cell_reserve_for_transfer(&pool, 1);
    assert(reserved);
    assert(!vector_reserve_region(reserved, 32, 1, 1, 2, 0));
    assert(!vector_reserve_region(reserved, 64, 1, 1, 1, 0));
    assert(vector_reserve_region(reserved, 32, 1, 1, 1, 0));
    unsigned char *position = vector_base(vector_items(reserved));
    Cell *temp = string_new(&pool, 32, NULL);
    assert(position < vector_base(vector_items(temp)));
    Cell *value = vector_construct_reserved(reserved, 1, &pool, 32, 1, 1, 1, 0, NULL);
    assert(value == reserved && vector_base(vector_items(value)) == position);
    cell_drop(temp);
    string_push_str(value, (CrustText){(const unsigned char *)"ok", 2});
    assert(string_view(value).bytes == position && string_byte_len(value) == 2);
    cell_drop(value);
    reserved = cell_reserve_for_transfer(&pool, 1);
    assert(reserved && storage.class_count == 1);
    assert(vector_reserve_region(reserved, 64, 1, 1, 1, 1));
    assert(storage.class_count == 2);
    position = vector_base(vector_items(reserved));
    temp = string_new(&pool, 64, NULL);
    assert(position < vector_base(vector_items(temp)));
    value = vector_construct_reserved(reserved, 1, &pool, 64, 1, 1, 1, 0, NULL);
    assert(vector_base(vector_items(value)) == position && string_byte_len(warm) == 0);
    cell_drop(temp);
    cell_drop(value);
    cell_drop(warm);
    source_close(&pool);
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_transfer_reservation_counts_holes_at_both_pool_limits(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(5, &storage);
    Cell *first = string_new(&pool, 32, NULL);
    Cell *hole_a = string_new(&pool, 32, NULL);
    Cell *middle = string_new(&pool, 32, NULL);
    Cell *hole_b = string_new(&pool, 32, NULL);
    Cell *last = string_new(&pool, 32, NULL);
    const unsigned char *a = string_view(hole_a).bytes;
    const unsigned char *b = string_view(hole_b).bytes;
    const unsigned char *live = string_view(middle).bytes;
    cell_drop(hole_a);
    cell_drop(hole_b);
    assert(!cell_reserve_for_transfer(&pool, 2));
    Cell *reserved = cell_reserve_for_transfer(&pool, 1);
    assert(reserved == hole_b);
    assert(!vector_reserve_region(reserved, 32, 1, 1, 2, 0));
    assert(vector_reserve_region(reserved, 32, 1, 1, 1, 0));
    Cell *temp = string_new(&pool, 32, NULL);
    assert(temp == hole_a && string_view(temp).bytes == a);
    Cell *value = vector_construct_reserved(reserved, VECTOR_REGION_RESERVED, &pool, 32, 1, 1, 1, 0, NULL);
    assert(value == reserved && string_view(value).bytes == b);
    string_push_str(value, (CrustText){(const unsigned char *)"ok", 2});
    assert(string_view(middle).bytes == live && string_byte_len(middle) == 0);
    cell_drop(temp);
    cell_drop(value);
    cell_drop(last);
    cell_drop(middle);
    cell_drop(first);
    source_close(&pool);
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_unannotated_vector_reserves_descending_front_before_temporary(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    Cell *reserved = cell_reserve_for_transfer(&pool, 1);
    assert(reserved);
    int early = vector_reserve_front(reserved, sizeof(int), _Alignof(int));
    assert(early == VECTOR_FRONT_RESERVED);
    GrowthSpan *front = &vector_items(reserved)->span.span;
    assert(front->front == GROWTH_HIGH && storage.stack.fronts[GROWTH_HIGH] == front);
    assert(!storage.stack.fronts[GROWTH_LOW]);
    Cell *temp = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    assert(vector_items(temp)->span.span.front == GROWTH_LOW);
    Cell *value = vector_construct_reserved(reserved, early, &pool, 0, sizeof(int), _Alignof(int), 0, 0, NULL);
    assert(value == reserved && &vector_items(value)->span.span == front);
    cell_drop(temp);
    const int batch[] = {10, 20};
    VectorItems *items = vector_items(value);
    assert(vector_try_extend(items, batch, 1));
    unsigned char *first = vector_item_at(items, 0);
    assert(vector_try_extend(items, batch + 1, 1));
    assert(vector_item_at(items, 0) == first);
    assert(memcmp(first, batch, sizeof(int)) == 0);
    assert(memcmp(vector_item_at(items, 1), batch + 1, sizeof(int)) == 0);
    cell_drop(value);
    source_close(&pool);

    pool = source_vector_pool(2, &storage);
    storage.stack = growth_stack(sizeof(int));
    reserved = cell_reserve_for_transfer(&pool, 1);
    assert(vector_reserve_front(reserved, sizeof(int), _Alignof(int)) == VECTOR_STORAGE_UNRESERVED);
    temp = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    assert(vector_try_extend(vector_items(temp), batch, 1));
    value = vector_construct_reserved(reserved, VECTOR_STORAGE_UNRESERVED,
                                     &pool, 0, sizeof(int), _Alignof(int), 0, 0, NULL);
    assert(vector_items(temp)->span.span.stack == &storage.stack);
    assert(vector_items(value)->span.span.stack == &vector_items(value)->span.dedicated);
    cell_drop(value);
    cell_drop(temp);
    source_close(&pool);
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_dedicated_reservation_leaves_shared_fronts_for_temporaries(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    for (int forward = 0; forward <= 1; ++forward) {
        VectorStorage storage = {0};
        Source pool = source_vector_pool(forward ? 2 : 3, &storage);
        Cell *reserved = cell_reserve_for_transfer(&pool, forward ? 1 : 2);
        int early = vector_reserve_dedicated_front(reserved, 1, 1);
        assert(early == VECTOR_DEDICATED_RESERVED && !storage.stack.mapping.base);
        unsigned char *origin = vector_base(vector_items(reserved));
        Cell *first = vector_new(&pool, 0, 1, 1, forward, NULL);
        assert(vector_items(first)->span.span.stack == &storage.stack);
        assert(vector_items(first)->span.span.front == GROWTH_LOW);
        Cell *second = NULL;
        if (!forward) {
            second = vector_new(&pool, 0, 1, 1, 0, NULL);
            assert(vector_items(second)->span.span.stack == &storage.stack);
            assert(vector_items(second)->span.span.front == GROWTH_HIGH);
        }
        Cell *value = vector_construct_reserved(reserved, early, &pool, 0, 1, 1, forward, 0, NULL);
        assert(value == reserved && vector_base(vector_items(value)) == origin);
        if (second) cell_drop(second);
        cell_drop(first);
        assert(vector_try_extend(vector_items(value), "ok", 2));
        assert(vector_base(vector_items(value)) == origin && memcmp(origin, "ok", 2) == 0);
        cell_drop(value);
        source_close(&pool);
    }
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_region_classes_and_both_fronts_share_live_capacity(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(4, &storage);
    size_t offset;
    size_t stride = growth_region_stride(32, &offset);
    storage.stack = growth_stack(4 * stride + 65);
    Cell *region = vector_new(&pool, 32, sizeof(int), _Alignof(int), 0, NULL);
    Cell *left = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    Cell *right = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    VectorItems *a = vector_items(left), *b = vector_items(right);
    assert(vector_items(region)->region.region.pool->slots.base == storage.stack.mapping.base + 64);
    assert(a->span.span.stack == &storage.stack && a->span.span.front == GROWTH_LOW);
    assert(b->span.span.stack == &storage.stack && b->span.span.front == GROWTH_HIGH);
    const int batch[] = {10, 20, 30, 40, 50, 60, 70, 80};
    assert(vector_try_extend(a, batch, 8));
    assert(vector_try_extend(b, batch, 8));
    unsigned char *first_a = vector_item_at(a, 0), *first_b = vector_item_at(b, 0);
    assert(!vector_try_extend(a, batch, 1));
    assert(!vector_try_extend(b, batch, 1));
    Cell *late = vector_new(&pool, 16, sizeof(int), _Alignof(int), 0, NULL);
    assert(vector_items(late)->region.dedicated.region_size == 16);
    cell_drop(late);
    cell_drop(region);
    assert(b->span.span.saved_cursor == 64 && !vector_try_extend(a, batch, 1));
    assert(vector_item_at(b, 0) == first_b && memcmp(first_b, batch, sizeof(int)) == 0);
    cell_drop(right);
    assert(storage.stack.high == storage.stack.mapping.capacity);
    assert(vector_try_extend(a, batch, 8));
    assert(vector_item_at(a, 0) == first_a && memcmp(first_a, batch, sizeof batch) == 0);
    Cell *reopened = vector_new(&pool, 32, sizeof(int), _Alignof(int), 0, NULL);
    assert(!vector_items(reopened)->region.dedicated.region_size);
    assert(storage.stack.high >= storage.stack.low);
    assert(vector_item_at(a, 0) == first_a && memcmp(first_a, batch, sizeof batch) == 0);
    cell_drop(reopened);
    cell_drop(left);
    source_close(&pool);
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_two_threads_share_growth_metadata(self):
        emitted = '#define CRUST_THREAD_RUNTIME 1\n' + compile_source("").replace(
            "int main(void)", "int crust_entry(void)")
        emitted = emitted.replace("#include <pthread.h>", "#include <pthread.h>\n#include <sched.h>")
        # Increase the chance of interleaving between the bounds check and cursor update.
        emitted = emitted.replace(
            "if (count > available / span->element_size) return NULL;",
            "if (count > available / span->element_size) return NULL; sched_yield();")
        harness = """
#include <assert.h>
typedef struct {
    Cell *cell;
    Source *pool;
    unsigned char byte;
    size_t length;
} Worker;

static void *fill(void *argument) {
    Worker *worker = argument;
    VectorItems *items = vector_items(worker->cell);
    while (vector_try_extend(items, &worker->byte, 1)) worker->length++;
    return NULL;
}

static void *reuse_regions(void *argument) {
    Worker *worker = argument;
    for (size_t i = 0; i < 400; ++i) {
        Cell *cell = string_new(worker->pool, i % 2 ? 32 : 48, NULL);
        string_push_str(cell, (CrustText){&worker->byte, 1, 0});
        assert(*text_address(string_view(cell), 0) == worker->byte);
        cell_drop(cell);
    }
    return NULL;
}

static void run_pair(void *(*run)(void *), Worker *first, Worker *second) {
    pthread_t a, b;
    assert(!pthread_create(&a, NULL, run, first));
    assert(!pthread_create(&b, NULL, run, second));
    assert(!pthread_join(a, NULL));
    assert(!pthread_join(b, NULL));
}

int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(4, &storage);
    for (size_t round = 0; round < 30; ++round) {
        storage.stack = growth_stack(257);
        Worker a = {vector_new(&pool, 0, 1, 1, 0, NULL), &pool, 'a', 0};
        Worker b = {vector_new(&pool, 0, 1, 1, 0, NULL), &pool, 'b', 0};
        run_pair(fill, &a, &b);
        assert(a.length + b.length == 257);
        assert(storage.stack.low == storage.stack.high);
        for (size_t i = 0; i < a.length; ++i) assert(*vector_item_at(vector_items(a.cell), i) == 'a');
        for (size_t i = 0; i < b.length; ++i) assert(*vector_item_at(vector_items(b.cell), i) == 'b');
        cell_drop(a.cell);
        cell_drop(b.cell);
        growth_close(&storage.stack);
    }
    Worker a = {NULL, &pool, 'a', 0};
    Worker b = {NULL, &pool, 'b', 0};
    run_pair(reuse_regions, &a, &b);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))

    def test_vector_items_keep_logical_order_on_both_fronts(self):
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = """
#include <assert.h>
static int read_item(VectorItems *items, size_t index) {
    int value;
    memcpy(&value, vector_item_at(items, index), sizeof value);
    return value;
}
int main(void) {
    VectorStorage storage = {0};
    Source pool = source_vector_pool(2, &storage);
    storage.stack = growth_stack(8 * sizeof(int));
    Cell *left = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    Cell *right = vector_new(&pool, 0, sizeof(int), _Alignof(int), 0, NULL);
    VectorItems *a = vector_items(left), *b = vector_items(right);
    assert(a->span.span.front == GROWTH_LOW && b->span.span.front == GROWTH_HIGH);
    assert(!vector_item_at(a, 0) && !vector_item_at(b, 0));
    const int batch[] = {10, 20, 30};
    assert(vector_try_extend(a, batch, 3));
    assert(vector_try_extend(b, batch, 3));
    unsigned char *first_a = vector_item_at(a, 0), *first_b = vector_item_at(b, 0);
    for (size_t i = 0; i < 3; ++i) {
        assert(read_item(a, i) == batch[i] && read_item(b, i) == batch[i]);
    }
    assert(!vector_try_extend(b, batch, 3));
    assert(!vector_try_extend(b, batch, SIZE_MAX));
    assert(a->length == 3 && b->length == 3);
    assert(vector_item_at(a, 0) == first_a && vector_item_at(b, 0) == first_b);
    int removed;
    vector_remove(right, 1, &removed);
    assert(removed == 20 && b->length == 2 && read_item(b, 1) == 30);
    vector_remove(left, 0, &removed);
    assert(removed == 10 && a->length == 2 && read_item(a, 0) == 20 && read_item(a, 1) == 30);
    assert(vector_try_extend(a, batch, 1));
    vector_truncate(b, 1);
    assert(!vector_item_at(b, 1) && vector_item_at(b, 0) == first_b);
    assert(vector_try_extend(b, (const int[]){40, 50, 60, 70}, 4));
    assert(vector_item_at(b, 0) == first_b && read_item(b, 4) == 70);
    assert(vector_item_at(a, 0) == first_a && read_item(a, 2) == 10);
    assert(vector_pop(right, &removed) == CRUST_CHAR_OK && removed == 70);
    assert(vector_pop(left, &removed) == CRUST_CHAR_OK && removed == 10);
    assert(vector_item_at(b, 0) == first_b && b->length == 4);
    assert(vector_try_extend(b, (const int[]){80}, 1) && read_item(b, 4) == 80);
    int incoming = 90;
    assert(vector_replace(right, 4, &incoming) == CRUST_VECTOR_OK);
    assert(incoming == 80 && read_item(b, 4) == 90);
    assert(vector_replace(right, 5, &incoming) == CRUST_VECTOR_REJECTED);
    assert(incoming == 80 && b->length == 5 && read_item(b, 4) == 90);
    assert(vector_item_at(b, 0) == first_b && a->length == 2);
    cell_drop(right);
    cell_drop(left);
    source_close(&pool);
    return 0;
}
"""
        self.native(emitted + harness, (([], ""),))
