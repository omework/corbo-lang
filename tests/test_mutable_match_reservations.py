"""Transitive holder reservations and source effects ordered by contracts."""
from functools import partial, update_wrapper
import unittest

from crust import verify_program

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
import test_mutable_match as match
from test_mutable_match_escape import IDENTITY
from test_mutable_match_function_return import OPEN, PREFIX

OPENERS = IDENTITY + OPEN
STORE = ('fn store(q:&mut Pool<W>,w:&mut W)-><-W{'
         'let mut r=open(w);let relay=new(q)W.Bound{data:r};return<-relay;}')
RELAY = 'let mut other=pool<W>(1);let mut relay=new(other)W.Bound{data:out};'
FINISH = 'fn finish(x:&mut Int,q:&mut Pool<W>,k:Int){%s}'
FINISH_CALL = 'finish(out,&mut q,%d);'


class MutableMatchReservationsTests(unittest.TestCase):
    execute = match.MutableMatchTests.execute
    with_source = match.MutableMatchTests.with_source
    run_source = match.MutableMatchTests.run_source
    reject = match.MutableMatchTests.reject

    def test_stored_reservation_and_transitive_reborrow(self):
        source = PREFIX + RELAY + 'let mut last=open(&mut relay);'
        self.reject(source + 'print(w);last.set(30);', 'emprunt actif')
        self.reject(source + 'print(relay);last.set(30);', 'emprunt actif')
        self.reject(source + 'q.reset();last.set(30);', 'reset')
        self.reject(source + 'other.reset();last.set(30);', 'reset')
        self.reject(source + 'last.set(30);print(w);print(relay);', 'emprunt actif')
        result = self.run_source(source + 'last.set(30);print(relay);print(w);print(n);')
        self.assertEqual(result.stdout, 'W.Bound(30)\nW.Bound(30)\n30\n')

    def test_stored_reservation_survives_opaque_owned_return(self):
        source = OPENERS + STORE + match.PREFIX + (
            'let mut other=pool<W>(1);let mut relay=store(&mut other,&mut w);')
        self.reject(source + 'print(w);print(relay);', 'emprunt actif')
        result = self.run_source(source + 'print(relay);print(w);')
        self.assertEqual(result.stdout, 'W.Bound(10)\nW.Bound(10)\n')

    def test_transfer_requires_a_durable_holder(self):
        source = OPENERS + match.DECL + match.SETUP + 'let mut other=pool<W>(1);'
        local_writer = source + 'let relay={' + match.HOLDER + (
            'let mut out=open(&mut w);let relay=new(other)W.Bound{data:out};<-relay};print(relay);')
        self.reject(local_writer, 'non durable')
        result = self.run_source(OPENERS + match.PREFIX + 'let mut other=pool<W>(1);'
            'let relay={let mut out=open(&mut w);'
            'let relay=new(other)W.Bound{data:out};<-relay};print(relay);print(w);')
        self.assertEqual(result.stdout, 'W.Bound(10)\nW.Bound(10)\n')

    def test_union_of_possible_holders(self):
        choose = ('fn choose(k:Int,a:&mut W,b:&mut W)->&mut Int{'
                  'if k==0{return open(a);}return open(b);}')
        source = OPENERS + choose + match.PREFIX + (
            'let mut q2=pool<W>(1);let mut n2=new(p)Int(11);'
            'let mut w2=new(q2)W.Bound{data:&mut n2};')
        for flag, expected in ((0, 'W.Bound(30)\nW.Bound(11)\n'),
                               (1, 'W.Bound(10)\nW.Bound(30)\n')):
            prefix = source + f'let mut out=choose({flag},&mut w,&mut w2);'
            for holder in ('w', 'w2'):
                self.reject(prefix + f'print({holder});out.set(30);', 'emprunt actif')
            self.assertEqual(self.run_source(prefix + 'out.set(30);print(w);print(w2);').stdout,
                             expected)

    def test_order_composes_and_is_visible_in_contract(self):
        helpers = 'fn touch(x:&mut Int){x.set(30);}fn clear(q:&mut Pool<W>){q.reset();}'
        for use, reset in (('x.set(30);', 'q.reset();'), ('touch(x);', 'clear(q);')):
            for body, allowed in ((use + reset, True), (reset + use, False)):
                with self.subTest(body=body):
                    source = helpers + FINISH % body + PREFIX + FINISH_CALL % 0 + 'print(n);'
                    if allowed:
                        self.assertEqual(self.run_source(source).stdout, '30\n')
                    else:
                        self.reject(source, 'porteur.*usage ultérieur')
        contracts = verify_program(match.DECL + helpers +
            (FINISH % 'clear(q);touch(x);')).function_contracts
        constraints = contracts['finish'].constraints.reservation_requirements
        self.assertEqual({(c.left.kind, c.left.index, c.right.kind, c.right.index) for c in constraints},
                         {('reservation_parameter', 0, 'source_parameter', 1)})

    def test_reset_paths_and_caller_join(self):
        body = 'if k==1{q.reset();}else{x.set(30);}'
        for flag, expected in ((0, '30\n'), (1, '10\n')):
            source = FINISH % body + PREFIX + FINISH_CALL % flag
            self.assertEqual(self.run_source(source + 'print(n);').stdout, expected)
            self.reject(source + 'print(w);', 'reset|plus utilisable')
            self.reject((FINISH % (body + 'x.set(40);')) + PREFIX + FINISH_CALL % flag,
                        'porteur.*usage ultérieur')

    def test_unpassed_live_borrow_blocks_pool_reset(self):
        source = FINISH % 'x.set(30);q.reset();' + PREFIX.replace(
            'q=pool<W>(1)', 'q=pool<W>(2)') + (
            'let mut n2=new(p)Int(20);let mut w2=new(q)W.Bound{data:&mut n2};'
            'let mut another=open(&mut w2);')
        self.reject(source + FINISH_CALL % 0 + 'another.set(40);', 'reset')
        result = self.run_source(source + 'another.set(40);' + FINISH_CALL % 0 +
                                 'print(n);print(n2);')
        self.assertEqual(result.stdout, '30\n40\n')

    def test_prepared_argument_protects_holder_during_nested_reset(self):
        funcs = ('fn clear(q:&mut Pool<W>)->Int{q.reset();return 1;}'
                 'fn edit(x:&mut Int,code:Int){x.set(30);print(code);}')
        source = funcs + PREFIX
        self.reject(source + 'edit(out,clear(&mut q));', 'argument en cours')
        self.assertEqual(self.run_source(source + 'edit(out,1);q.reset();print(n);').stdout,
                         '1\n30\n')

    def test_loop_backedge_is_another_use(self):
        safe = FINISH % 'loop{x.set(30);q.reset();break;}'
        unsafe = FINISH % 'loop{x.set(30);q.reset();if k==0{break;}}'
        call = PREFIX + FINISH_CALL % 1 + 'print(n);'
        self.assertEqual(self.run_source(safe + call).stdout, '30\n')
        self.reject(unsafe + call, 'porteur.*usage ultérieur')
