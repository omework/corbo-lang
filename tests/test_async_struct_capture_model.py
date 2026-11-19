"""Independent finite loan table for a borrowed structure and its caller."""
import unittest
from crust import Error, verify_program
import test_async_struct_captures as structures


class StructCaptureLoanModel(unittest.TestCase):
    run_c_oracle = structures.AsyncStructCaptureTests.run_c_oracle
    run_native = structures.AsyncStructCaptureTests.run_native

    def test_access_matrix_before_and_after_wait(self):
        accepted=rejected=0
        for exclusive in (False,True):
            mode='&mut ' if exclusive else '&'
            result=8 if exclusive else 7
            worker=f'''async fn work(p:{mode}Point)->Int{{yield;
              {'p.x=p.x+1;' if exclusive else ''}return p.x;}}'''
            for after in (False,True):
                for operation in ('none','read','write','drop'):
                    # The task retains its loan from creation until wait. The
                    # caller can only read during a shared loan. A completed
                    # task no longer reserves this target (its result is Int).
                    expected=after or operation=='none' or operation=='read' and not exclusive
                    action={'none':'','read':'print(p.x);','write':'p.x=20;print(p.x);','drop':'drop(->p);'}[operation]
                    wait='let h=runtime::spawn(->task);match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}'
                    body=f'let mut p=Point{{x:7,y:9}};let task=work({mode}p);'+(wait+action if after else action+wait)
                    source=structures.AsyncStructCaptureTests.wrap(worker,body)
                    with self.subTest(exclusive=exclusive,after=after,operation=operation):
                        if not expected:
                            with self.assertRaises(Error):verify_program(source)
                            rejected+=1
                            continue
                        observations=[]
                        if operation=='read':observations.append(result if after else 7)
                        elif operation=='write':observations.append(20)
                        observations=([result]+observations) if after else (observations+[result])
                        self.assertEqual(self.run_native(source).stdout,''.join(f'{x}\n' for x in observations))
                        accepted+=1
        self.assertEqual((accepted,rejected),(11,5))


if __name__=='__main__':unittest.main()
