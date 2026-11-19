"""Finite independent two-link lifetime model: task -> holder -> integer."""
import unittest
from crust import Error, verify_program
import test_async_struct_reference_fields as fields


class TransitiveCaptureModel(unittest.TestCase):
    run_c_oracle = fields.AsyncStructReferenceFieldTests.run_c_oracle
    run_native = fields.AsyncStructReferenceFieldTests.run_native

    def test_target_access_matrix(self):
        admitted=refused=0
        for exclusive in (False,True):
            for waited in (False,True):
                for action in ('none','read','write','drop'):
                    # The integer is reachable through two lifetime edges. Waiting
                    # removes the task edge. With no subsequent holder use, its
                    # loan expires too; the scalar result carries no dependency.
                    allowed=waited or action=='none' or action=='read' and not exclusive
                    statement={'none':'','read':'print(data);','write':'data=20;print(data);',
                               'drop':'drop(->data);'}[action]
                    wait='let h=runtime::spawn(->t);match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}'
                    mode='&mut' if exclusive else '&'
                    main=f'let t=work({mode} v);'+(wait+statement if waited else statement+wait)
                    source=fields.AsyncStructReferenceFieldTests.program(mutable=exclusive,main=main)
                    with self.subTest(exclusive=exclusive,waited=waited,action=action):
                        if not allowed:
                            with self.assertRaises(Error):verify_program(source)
                            refused+=1
                            continue
                        extra=[7] if action=='read' else [20] if action=='write' else []
                        observed=[7]+extra if waited else extra+[7]
                        self.assertEqual(self.run_native(source).stdout,''.join(f'{n}\n' for n in observed))
                        admitted+=1
        self.assertEqual((admitted,refused),(11,5))


if __name__=='__main__':unittest.main()
