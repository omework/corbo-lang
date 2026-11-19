"""Independent finite field-disjointness and lifetime table."""
import unittest
from crust import Error,verify_program
import test_async_field_reborrows as fields


class FieldReborrowModel(unittest.TestCase):
    run_c_oracle=fields.AsyncFieldReborrowTests.run_c_oracle
    run_native=fields.AsyncFieldReborrowTests.run_native

    def test_field_access_before_and_after_last_use(self):
        admitted=refused=0
        for alias in (False,True):
            for held in ('left','data'):
                for touched in ('left','data'):
                    for after in (False,True):
                        for write in (False,True):
                            allowed=after or held!=touched
                            root='alias' if alias else 'v'
                            target=f'&mut {root}.left' if held=='left' else f'&mut *{root}.data'
                            init='{let alias=&mut *v;'+target+'}' if alias else target
                            read='v.left' if touched=='left' else '*v.data'
                            action=(('v.left=90;print(v.left);' if touched=='left' else
                                     'let q=&mut *v.data;q.set(90);print(*q);') if write else f'print({read});')
                            use='yield;r.set(31);print(*r);'
                            body=f'let r={init};'+(use+action if after else action+use)+'return v.left+*v.data;'
                            source=fields.AsyncFieldReborrowTests.program(body)
                            with self.subTest(alias=alias,held=held,touched=touched,after=after,write=write):
                                if not allowed:
                                    with self.assertRaises(Error):verify_program(source)
                                    refused+=1
                                    continue
                                values={'left':2,'data':7}
                                output=[]
                                # Explicit model state, independent of compiler loans or layout.
                                for event in (('use','action') if after else ('action','use')):
                                    if event=='use':
                                        values[held]=31;output.append(31)
                                    else:
                                        if write:values[touched]=90
                                        output.append(values[touched])
                                output.extend((sum(values.values()),values['left'],3,values['data']))
                                self.assertEqual(self.run_native(source).stdout,''.join(f'{n}\n' for n in output))
                                admitted+=1
        self.assertEqual((admitted,refused),(24,8))


if __name__=='__main__':unittest.main()
