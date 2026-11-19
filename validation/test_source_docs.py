# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused regressions for source documentation extraction, not language checking."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from source_docs import inventory,flatten,documentation,c_inventory,c_documentation


class DocumentationInventory(unittest.TestCase):
    """Check members, contracts and native-code exclusion at documentation boundaries."""
    def test_contract_and_native_code(self):
        source='''/// Owns a generic value.
#(type: T with { fn read(&self) -> i64; })
pub struct Box<T> {
    /// Stored value.
    item: T,
}
impl Box<T> {
    /// Returns one value.
    fn read(&self) -> i64 { @unchecked { @c { struct Hidden { int n; }; } } 1 }
}
'''
        entries,ann=inventory(source)
        self.assertEqual([(e.kind,e.name)for e in flatten(entries)],[('struct','Box'),('field','item'),('fn','read')])
        self.assertEqual(entries[1].owner,'Box')
        self.assertTrue(all(documentation(source,e,ann)for e in flatten(entries)))
    def test_nested_payload_and_function_type(self):
        source='''/// Container.
struct C {
 /// Function.
 call: fn(i64, i64) -> i64,
}
/// Outcome.
enum E {
 /// Failure.
 Error {
   /// Status.
   code: i64,
 },
}
'''
        entries,ann=inventory(source)
        self.assertEqual([e.name for e in flatten(entries)],['C','call','E','Error','code'])
        self.assertTrue(all(documentation(source,e,ann)for e in flatten(entries)))
    def test_missing_field_comment_is_visible(self):
        source='/// Container.\nstruct C { value: i64 }'
        entries,ann=inventory(source)
        self.assertFalse(documentation(source,entries[0].children[0],ann))
    def test_conditions(self):
        entries,_=inventory('#(if: target.os == "linux")\n/// Function.\npub fn f() {}\n#(endif)\n/// Other.\nfn g(){}')
        self.assertEqual(entries[0].conditions,('target.os == "linux"',))
        self.assertEqual(entries[1].conditions,())
    def test_c_functions_not_body_calls(self):
        source='''#include <stdint.h>
/** A callback container. */
typedef struct {
/** Destructor callback. */
void (*drop)(void *);
} Value;
/** Destroys a value. */
static void finish(Value *value) { value->drop(value); }
/** Creates a value. */
Value *create(void);
'''
        entries=c_inventory(source)
        self.assertEqual([(e.kind,e.name)for e in entries],[('c_type','Value'),('c_fn','finish'),('c_fn','create')])
        self.assertTrue(all(c_documentation(source,e)for e in flatten(entries)))


if __name__=='__main__': unittest.main()
