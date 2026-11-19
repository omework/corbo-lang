"""Native storage checks for HM1, HM2, HM4 and HM5."""
import unittest

from crust import compile_source
from hashmap_runtime import HASHMAP_RUNTIME
import test_async_runtime


class HashMapRuntimeTests(unittest.TestCase):
    run_c_oracle = test_async_runtime.AsyncRuntimeTests.run_c_oracle

    def run_map(self, body, expected_error=None):
        code = '#define main original_main\n' + compile_source('fn main(){}')
        code += '\n#undef main\n#include <assert.h>\n' + HASHMAP_RUNTIME + body
        return self.run_c_oracle(code, expected_error)

    def test_growth_collision_and_slot_reuse_keep_addresses_stable(self):
        self.run_map(r'''
static int dropped;
static void record_drop(void *value) { dropped += *(int32_t *)value; }
int main(void) {
    CrustHashMap map = crust_map_new(4096, sizeof(int32_t), _Alignof(int32_t));
    int32_t first = 10, second = 20, third = 30, previous = -1;
    assert(!crust_map_insert(&map, 0, &first, &previous));
    uint64_t collision = 1;
    while (crust_map_home(&map, collision) != crust_map_home(&map, 0)) ++collision;
    assert(!crust_map_insert(&map, collision, &second, &previous));
    void *stable = crust_map_get(&map, collision);
    assert(stable && *(int32_t *)stable == 20);
    assert(crust_map_remove(&map, 0, &previous) && previous == 10);
    assert(crust_map_get(&map, collision) == stable);
    assert(!crust_map_insert(&map, 100, &third, &previous));
    assert(map.slots == 2 && map.count == 2);
    for (uint64_t key = 101; key < 127; ++key) {
        int32_t value = (int32_t)key;
        if (key != collision) assert(!crust_map_insert(&map, key, &value, &previous));
    }
    assert(map.bucket_count > 4 && crust_map_get(&map, collision) == stable);
    assert(crust_map_remove(&map, collision, &previous) && previous == 20);
    assert(!crust_map_get(&map, collision));
    int expected = 30;
    for (uint64_t key = 101; key < 127; ++key) {
        if (key == collision) continue;
        assert(*(int32_t *)crust_map_get(&map, key) == (int32_t)key);
        expected += (int)key;
    }
    crust_map_drop(&map, record_drop);
    assert(dropped == expected);
}
''')

    def test_capacity_failure_preserves_state_and_replacement_succeeds(self):
        program = r'''
int main(void) {
    CrustHashMap probe = crust_map_new(4096, sizeof(int32_t), _Alignof(int32_t));
    size_t limit = probe.stride + 4 * sizeof(size_t);
    crust_map_drop(&probe, NULL);
    CrustHashMap map = crust_map_new(limit, sizeof(int32_t), _Alignof(int32_t));
    int32_t a = 10, b = 20, previous = -1;
    assert(crust_map_try_insert(&map, 1, &a, &previous) == CRUST_MAP_INSERTED);
    void *original = crust_map_get(&map, 1);
    FAILING_INSERT
    assert(previous == -1 && b == 20);
    assert(map.slots == 1 && map.count == 1 && !crust_map_get(&map, 2));
    assert(crust_map_get(&map, 1) == original && *(int32_t *)original == 10);
    assert(crust_map_try_insert(&map, 1, &b, &previous) == CRUST_MAP_REPLACED);
    assert(previous == 10 && *(int32_t *)original == 20);
    crust_map_drop(&map, NULL);
}
'''
        self.run_map(program.replace('FAILING_INSERT',
            'assert(crust_map_try_insert(&map, 2, &b, &previous) == CRUST_MAP_FULL);'))
        self.run_map(program.replace('FAILING_INSERT', 'crust_map_insert(&map, 2, &b, &previous);'),
                     'capacité de la HashMap dépassée')
