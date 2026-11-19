"""Replacement behind recursive links carries new sources and cleans old slots."""
import unittest
import test_select_source as harness
from test_recursive_borrow_projections import PEEK

TYPES='struct Leaf{item:A<Int>}enum Node{End{value:A<Leaf>},Link{next:A<Node>}}'
EDIT=PEEK.replace('fn peek(n:&Node)','fn edit(n:&mut Node,p:&mut Pool<Int>)').replace('match &','match &mut ').replace('print(*v);','v.item=<-p.new(9);').replace('print(0);','')
READ=PEEK.replace('print(*v);','print(*v.item);')
SETUP='''let mut old=pool<Int>(1);let first=old.new(7);
let mut fresh=pool<Int>(1);let mut leaves=pool<Leaf>(1);let leaf=leaves.new(item:<-first);
let mut nodes=pool<Node>(3);let end=new(nodes)Node.End{value:<-leaf};
let middle=new(nodes)Node.Link{next:<-end};let mut top=new(nodes)Node.Link{next:<-middle};'''

class RecursiveOwnedReplacementTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_replace_deep_leaf_and_reuse_old_slot(self):
        for asynchronous in (False,True):
            with self.subTest(asynchronous=asynchronous):
                body=SETUP+'''edit(&mut top,&mut fresh);PAUSE peek(&top);
let reused=old.new(11);print(*reused);drop(->top);let again=fresh.new(12);print(*again);'''
                body=body.replace('PAUSE','yield;' if asynchronous else '')
                source=(self.program(body+'return 1;',TYPES+EDIT+READ) if asynchronous else
                        TYPES+EDIT+READ+'fn main(){'+body+'}')
                run=self.run_source(source)
                self.assertEqual(run.stdout,'9\n11\n12\n'+('1\n' if asynchronous else ''))
                destructions=[line for line in run.stderr.splitlines() if line.startswith('destroy ')]
                self.assertEqual(sum(line.endswith('=7') for line in destructions),1)
                self.assertEqual(sum(line.endswith('=9') for line in destructions),1)
                self.refused(source.replace('edit(&mut top,&mut fresh);',
                    '{let mut short=pool<Int>(1);edit(&mut top,&mut short);}'),
                    'transfert refusé.*survit')

if __name__=='__main__':unittest.main()
