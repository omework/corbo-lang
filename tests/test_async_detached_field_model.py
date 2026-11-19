"""Independent finite lifetime model: a returned pointer retains its storage."""
import unittest
from crust import Error, verify_program, compile_source
import test_async_detached_field_returns as fixtures


class DetachedLifetimeModel(unittest.TestCase):
    run_native = fixtures.AsyncDetachedFieldTests.run_native
    run_c_oracle = fixtures.AsyncDetachedFieldTests.run_c_oracle

    def test_storage_and_last_use(self):
        accepted = rejected = 0
        for detached in (False, True):
            storage = 'target' if detached else 'carrier'
            body = 'yield;return v.data;' if detached else 'yield;return &v.left;'
            for action, invalidated in (
                    ('drop(->v);', {'carrier'}),
                    ('v.left=90;', {'carrier'}),
                    ('drop(->v);drop(->data);', {'carrier', 'target'})):
                for after in (False, True):
                    expected = after or storage not in invalidated
                    use = 'print(r);' + action if after else action + 'print(r);'
                    source = fixtures.AsyncDetachedFieldTests.program(body, use=use)
                    source = source.replace(' print(data);}', '}')
                    with self.subTest(detached=detached, action=action, after=after):
                        if expected:
                            self.assertEqual(self.run_native(source).stdout, '7\n' if detached else '2\n')
                            accepted += 1
                        else:
                            for check in (verify_program, compile_source):
                                with self.assertRaises(Error): check(source)
                            rejected += 1
        self.assertEqual((accepted, rejected), (8, 4))


if __name__ == '__main__': unittest.main()
