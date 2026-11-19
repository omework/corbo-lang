"""Pool aliases do not change the independent lexical ancestry criterion."""
import unittest
from crust import Error,verify_program
import test_async_local_pools as local_pools


class PoolAliasAncestryModel(unittest.TestCase):
    run_c_oracle=local_pools.AsyncLocalPoolTests.run_c_oracle
    run_native=local_pools.AsyncLocalPoolTests.run_native
    assert_destroyed=local_pools.AsyncLocalPoolTests.assert_destroyed

    def test_pool_depth_must_not_exceed_receiver_depth_for_an_owner(self):
        accepted=rejected=0
        for pool_depth in range(3):
            for receiver_depth in range(2):
                for owner in (False,True):
                    # A copied integer is independent; an allocation retains
                    # its source. Depth increases when entering a child.
                    expected=not owner or pool_depth<=receiver_depth
                    pools=['let mut p=pool<Int>(1);' if depth==pool_depth else '' for depth in range(3)]
                    inner=pools[2]+'let memory=&mut p;let inner=&mut *memory;let a=child(inner).await;yield;'+('<-a' if owner else '*a')
                    middle=pools[1]+'let middle={'+inner+'};'
                    if receiver_depth==0:
                        middle+='<-middle' if owner else 'middle'
                    else:
                        middle+=('print(*middle);drop(->middle);' if owner else 'print(middle);')+'7'
                    body=pools[0]+'let result={'+middle+'};return '+('*result;' if owner and receiver_depth==0 else 'result;')
                    source=local_pools.AsyncLocalPoolTests.wrap(body, 'async fn child(p:&mut Pool<Int>)-><-Int{yield;return <-p.new(7);}')
                    with self.subTest(pool_depth=pool_depth,receiver_depth=receiver_depth,owner=owner):
                        if expected:
                            run=self.run_native(source)
                            self.assertEqual(run.stdout,'7\n'*(1+receiver_depth))
                            self.assert_destroyed(run,[7]);accepted+=1
                        else:
                            with self.assertRaisesRegex(Error,'pool local'):verify_program(source)
                            rejected+=1
        self.assertEqual((accepted,rejected),(9,3))


if __name__=='__main__':unittest.main()
