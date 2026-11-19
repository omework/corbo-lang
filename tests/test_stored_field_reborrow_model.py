"""Finite capability graph independent of compiler paths and C pointers."""
import unittest
from crust import Error, verify_program, compile_source
import test_stored_field_reborrows as fixtures


class StoredCapabilityModel(unittest.TestCase):
    run_native = fixtures.StoredFieldReborrowTests.run_native
    run_c_oracle = fixtures.StoredFieldReborrowTests.run_c_oracle

    def test_transitive_capability_until_last_use(self):
        # Result -> writer.data capability -> target; result does not hold View.
        held = {'writer', 'writer.data', 'target'}
        actions = (
            ('drop(->writer);', {'writer'}),
            ('drop(->writer);drop(->data);', {'writer', 'target'}),
            ('writer.spare=9;', {'writer.spare'}),
            ('let mut other=&mut *writer.data;other.set(9);', {'writer.data', 'target'}))
        accepted = rejected = 0
        for helper in (False, True):
            helpers = 'fn target(w:&mut Writer)->&Int{return &*w.data;}' if helper else ''
            base = fixtures.StoredFieldReborrowTests.program(
                'target(&mut writer)' if helper else '&*writer.data',
                use='', helpers=helpers, async_result=True)
            base = base.replace('drop(->writer);print(data);', '')
            for code, writes in actions:
                for after in (False, True):
                    source = base.replace('print(r);', 'print(r);'+code if after else code+'print(r);')
                    with self.subTest(helper=helper, code=code, after=after):
                        if after or not held.intersection(writes):
                            self.assertEqual(self.run_native(source).stdout, '7\n')
                            accepted += 1
                        else:
                            for check in (verify_program, compile_source):
                                with self.assertRaises(Error): check(source)
                            rejected += 1
        self.assertEqual((accepted, rejected), (10, 6))


if __name__ == '__main__': unittest.main()
