"""An escaping match projection holds both its target and its writer."""
import unittest

import test_mutable_match as match

IDENTITY = 'fn identity(x:&mut Int)->&mut Int{return x;}'
MATCH = ('let mut out=match &mut w{W.Bound{data:r}=>{'
         'let mut child=identity(r);child}};')
PREFIX = IDENTITY + match.PREFIX + MATCH


class MutableMatchEscapeTests(unittest.TestCase):
    execute = match.MutableMatchTests.execute
    with_source = match.MutableMatchTests.with_source
    run_source = match.MutableMatchTests.run_source
    reject = match.MutableMatchTests.reject

    def test_writer_reopens_after_last_use_of_result(self):
        self.reject(PREFIX + 'print(w);out.set(30);', 'emprunt actif')
        result = self.run_source(PREFIX + 'out.set(30);print(w);print(n);')
        self.assertEqual(result.stdout, 'W.Bound(30)\n30\n')
        self.assertEqual([line for line in result.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy w=W.Bound', 'destroy n=30'])

    def test_holder_and_target_remain_alive(self):
        for action in ('drop(->w);', 'drop(->n);', 'q.reset();', 'p.reset();',
                       'w=new(q)W.Bound{data:&mut n};'):
            with self.subTest(action=action):
                self.reject(PREFIX + action + 'out.set(30);', 'emprunt|reset')
        result = self.run_source(PREFIX + 'out.set(30);q.reset();p.reset();')
        self.assertEqual(result.stderr.count('destroy n=30'), 1)

    def test_forwarded_reference_keeps_writer_reserved(self):
        prefix = PREFIX + 'let mut next=identity(out);'
        self.reject(prefix + 'print(w);next.set(30);', 'emprunt actif')
        self.assertEqual(self.run_source(prefix + 'next.set(30);print(w);').stdout,
                         'W.Bound(30)\n')

    def test_opaque_call_cannot_reset_the_holder_of_an_argument(self):
        clear = 'fn clear(q:&mut Pool<W>,x:&mut Int){q.reset();x.set(30);}'
        self.reject(PREFIX + clear + 'clear(&mut q,out);', 'porteur.*réservé')

    def test_other_fields_of_writer_are_preserved(self):
        prefix = ('enum W{Bound{data:&mut Int,other:&mut Int}}'
                  'let mut p=pool<Int>(2);let mut q=pool<W>(1);'
                  'let mut n=new(p)Int(10);let mut m=new(p)Int(11);'
                  'let mut w=new(q)W.Bound{data:&mut n,other:&mut m};'
                  'let mut out=match &mut w{W.Bound{data:r,other:_}=>{r}};')
        self.reject(prefix + 'drop(->m);out.set(30);print(w);', 'emprunt actif|emprunt encore')
        self.assertEqual(self.run_source(prefix + 'out.set(30);print(w);').stdout,
                         'W.Bound(30, 11)\n')

    def test_possible_arms_preserve_both_target_provenances(self):
        prefix = ('enum W{A{x:&mut Int},B{x:&mut Int}}'
                  'fn make(q:&mut Pool<W>,a:&mut Int,b:&mut Int,k:Int)-><-W{'
                  'if k==0{let w=new(q)W.A{x:a};return<-w;}'
                  'let w=new(q)W.B{x:b};return<-w;}'
                  'let mut p=pool<Int>(2);let mut q=pool<W>(1);'
                  'let mut a=new(p)Int(10);let mut b=new(p)Int(11);')
        for k, expected in ((0, 'W.A(30)\n30\n11\n'), (1, 'W.B(30)\n10\n30\n')):
            with self.subTest(variant=k):
                source = (prefix + f'let mut w=make(&mut q,&mut a,&mut b,{k});' +
                          'let mut out=match &mut w{W.A{x:r}=>{r},W.B{x:r}=>{r}};')
                self.reject(source + 'print(w);out.set(30);', 'emprunt actif')
                self.assertEqual(self.run_source(source + 'out.set(30);print(w);print(a);print(b);').stdout,
                                 expected)

    def test_arms_must_produce_a_projection_and_binding_stays_local(self):
        self.reject(PREFIX.replace('child}};', 'n}};') + 'out.set(30);', 'réemprunt mutable')
        self.reject(PREFIX.replace('child}};', 'print(child);}};') + 'out.set(30);',
                    'chaque bras')
        local = ('fn bad(q:&mut Pool<W>,n:&mut Int)->&mut Int{'
                 'let mut w=new(q)W.Bound{data:n};' + MATCH + 'return out;}')
        self.reject(local + match.DECL + IDENTITY, 'non durable')
