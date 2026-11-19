"""Replacing an A<Node> link destroys its former subtree and changes provenance."""
import unittest
import test_select_source as harness

TYPES='struct Link{node:A<Node>}enum Node{End{value:Int},Link{next:A<Link>}}'
EDIT='''fn edit(root:&mut Node,p:&mut Pool<Node>){match &mut root{
Node.End{value:_}=>{},Node.Link{next:link}=>{link.node=<-new(p)Node.End{value:9};}}}'''
READ='''fn peek(root:&Node){match &root{Node.End{value:v}=>{print(v);},
Node.Link{next:link}=>{let child=&*link.node;match &child{
Node.End{value:v}=>{print(v);},Node.Link{next:_}=>{print(0);}}}}}'''
SETUP='''let mut nodes=pool<Node>(3);let mut links=pool<Link>(2);
let end=new(nodes)Node.End{value:7};let inside=links.new(node:<-end);
let middle=new(nodes)Node.Link{next:<-inside};let outside=links.new(node:<-middle);
let mut top=new(nodes)Node.Link{next:<-outside};let mut fresh=pool<Node>(1);'''

class RecursiveLinkReplacementTests(unittest.TestCase):
    run_source=harness.SelectSourceTests.run_source
    run_c_oracle=harness.SelectSourceTests.run_c_oracle
    refused=harness.SelectSourceTests.refused
    program=staticmethod(harness.SelectSourceTests.program)

    def test_replace_recursive_subtree_and_reuse_slots(self):
        for asynchronous in (False,True):
            with self.subTest(asynchronous=asynchronous):
                body=SETUP+'''edit(&mut top,&mut fresh);PAUSE peek(&top);
let again=new(nodes)Node.End{value:11};let reused=links.new(node:<-again);
drop(->reused);drop(->top);let last=new(fresh)Node.End{value:12};peek(&last);'''
                body=body.replace('PAUSE','yield;' if asynchronous else '')
                source=(self.program(body+'return 1;',TYPES+EDIT+READ) if asynchronous else
                        TYPES+EDIT+READ+'fn main(){'+body+'}')
                run=self.run_source(source)
                self.assertEqual(run.stdout,'9\n12\n'+('1\n' if asynchronous else ''))
                for name in ('end','inside','middle','outside','top'):
                    self.assertEqual(sum(line.startswith('destroy '+name+'=') for line in run.stderr.splitlines()),1)
                self.refused(source.replace('edit(&mut top,&mut fresh);',
                    '{let mut short=pool<Node>(1);edit(&mut top,&mut short);}'),
                    'transfert refusé.*survit')

    def test_read_projection_still_checks_mutability_and_field(self):
        source=TYPES+READ+'fn main(){'+SETUP+'peek(&top);}'
        self.refused(source.replace('let child=&*link.node;',
            'let mut child=&mut *link.node;'),'mutable|lecture|immuable')
        self.refused(source.replace('&*link.node','&*link.missing'),'champ|inconnu')

if __name__=='__main__':unittest.main()
