"""Finite result-path model: roots live until the last result use."""
import unittest
from crust import Error, verify_program
import test_async_field_reference_returns as fixtures


class FieldReturnModel(unittest.TestCase):
    run_c_oracle=fixtures.AsyncFieldReturnTests.run_c_oracle
    run_native=fixtures.AsyncFieldReturnTests.run_native
    make_program=staticmethod(fixtures.AsyncFieldReturnTests.program)

    def test_result_path_union_and_last_use(self):
        accepted=rejected=0
        for union in (False,True):
            held={'data','left'} if union else {'data'}
            body=('yield;return if 1==1 {&mut *v.data} else {&mut v.left};' if union else
                  'yield;return &mut *v.data;')
            for touched in ('left','data','right'):
                for after in (False,True):
                    for write in (False,True):
                        access={'left':'v.left','data':'*v.data','right':'v.right'}[touched]
                        action=f'print({access});'
                        if write:
                            action=(f'{access}=90;' if touched!='data' else
                                    'let other=&mut *v.data;other.set(90);')+action
                        use='n.set(31);print(n);'
                        source=self.make_program(body,use=use+action if after else action+use)
                        with self.subTest(union=union,touched=touched,after=after,write=write):
                            if not after and touched in held:
                                with self.assertRaises(Error):verify_program(source)
                                rejected+=1
                                continue
                            values={'left':2,'data':7,'right':3}
                            output=[]
                            for event in (('use','action') if after else ('action','use')):
                                if event=='use':values['data']=31;output.append(31)
                                else:
                                    if write:values[touched]=90
                                    output.append(values[touched])
                            output.extend(values[field] for field in ('left','right','data'))
                            self.assertEqual(self.run_native(source).stdout,''.join(f'{v}\n' for v in output))
                            accepted+=1
        self.assertEqual((accepted,rejected),(18,6))


if __name__=='__main__':unittest.main()
