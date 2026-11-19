"""Void calls reborrow projections while the match retains its reservation."""
import unittest

import test_mutable_match as match

EDIT = 'fn edit(x:&mut Int){x.set(20);}'
FORWARD = 'fn forward(x:&mut Int){edit(x);}'
PREFIX = EDIT + FORWARD + match.PREFIX


class MutableMatchCallTests(unittest.TestCase):
    execute = match.MutableMatchTests.execute
    with_source = match.MutableMatchTests.with_source
    reject = match.MutableMatchTests.reject
    run_source = match.MutableMatchTests.run_source

    def test_forwarded_reborrow_returns_to_the_arm(self):
        result = self.run_source(PREFIX + match.match_arm(
            '{forward(r);}print(r);r.set(21);edit(r);print(r);') +
            'print(w);print(n);')
        self.assertEqual(result.stdout, '20\n20\nW.Bound(20)\n20\n')
        self.assertEqual([line for line in result.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy w=W.Bound', 'destroy n=20'])

    def test_lifetime_boundaries_after_call(self):
        for arm, tail in [('edit(r);print(n);', ''), ('edit(r);', 'print(n);print(w);')]:
            with self.subTest(arm=arm, tail=tail):
                self.reject(PREFIX + match.match_arm(arm) + tail, 'emprunt actif')
        result = self.run_source(PREFIX + match.match_arm('edit(r);') +
                                 'print(w);p.reset();q.reset();')
        self.assertEqual(result.stdout, 'W.Bound(20)\n')
        self.assertEqual(result.stderr.count('destroy n=20'), 1)

    def test_call_keeps_projection_mode_and_exclusivity(self):
        duo = 'fn duo(x:&mut Int,y:&Int){x.set(20);print(y);}'
        self.reject(PREFIX + duo + match.match_arm('duo(r,r);'), 'aliasés')
        shared = ('enum W{Bound{data:&Int}}' + match.SETUP +
                  match.HOLDER.replace('&mut n', '&n'))
        self.reject(EDIT + shared + match.match_arm('edit(r);'), 'lecture')
        self.reject(PREFIX + match.match_arm('edit(&mut r);'), 'par leur nom')

    def test_call_cannot_receive_external_capabilities_or_return_a_loan(self):
        self.reject(PREFIX + match.match_arm('edit(n);'), 'projections')
        reset = 'fn reset(x:&mut Int,p:&mut Pool<Int>){x.set(20);p.reset();}'
        self.reject(PREFIX + reset + match.match_arm('reset(r,&mut p);'), 'projections')
        ret = 'fn identity(x:&mut Int)->&mut Int{return x;}'
        self.reject(PREFIX + ret + match.match_arm('identity(r);'), 'Void')
        self.reject(PREFIX + ret + match.match_arm('let other=identity(r);'), 'let mut')
        self.reject(PREFIX + match.match_arm('edit(r);', mode='&'), 'lecture uniquement')

    def test_unreachable_variant_validates_call_without_a_target(self):
        decl = 'enum W{Bound{data:&mut Int},Other{data:&mut Int}}'
        source = EDIT + decl + match.SETUP + match.HOLDER
        arm = ('match &mut w{W.Bound{data:r}=>{edit(r);},'
               'W.Other{data:r}=>{%s}}print(n);')
        self.assertEqual(self.run_source(source + arm % 'edit(r);').stdout, '20\n')
        self.reject(source + arm % 'edit(r,r);', 'attend 1 argument')

    def test_divergence_in_another_variant_preserves_the_continuation(self):
        decl = 'enum W{Bound{data:&mut Int},Other{data:&mut Int}}'
        funcs = ('fn stop(x:&mut Int){loop{}}' + EDIT +
                 'fn run(w:&mut W){match &mut w{W.Other{data:r}=>{stop(r);},'
                 'W.Bound{data:r}=>{edit(r);}}print(w);}')
        result = self.run_source(decl + funcs + match.SETUP + match.HOLDER +
                                 'run(&mut w);print(n);')
        self.assertEqual(result.stdout, 'W.Bound(20)\n20\n')

    def test_scalar_result_is_a_copy_and_projection_resumes(self):
        read = 'fn read(x:&Int)->Int{return *x;}'
        result = self.run_source(read + PREFIX + match.match_arm(
            'let value=read(r);r.set(20);print(value);print(r);') +
            'print(w);print(n);')
        self.assertEqual(result.stdout, '10\n20\nW.Bound(20)\n20\n')
        self.reject(read + PREFIX + match.match_arm('let value=read(r);print(value);print(n);'),
                    'emprunt actif')
        self.reject(read + PREFIX + match.match_arm('let value=read(r);print(value);') +
                    'print(value);', 'inconnue')

    def test_scalar_result_in_impossible_arm(self):
        decl = 'enum W{Bound{data:&mut Int},Other{data:&mut Int}}'
        source = 'fn read(x:&Int)->Int{return *x;}' + decl + match.SETUP + match.HOLDER
        arm = ('match &mut w{W.Bound{data:r}=>{let value=read(r);print(value);},'
               'W.Other{data:r}=>{let value=%s;print(value);}}')
        self.assertEqual(self.run_source(source + arm % 'read(r)').stdout, '10\n')
        self.reject(source + arm % 'read(r,r)', 'attend 1 argument')

    def test_returned_mutable_reborrow_ends_at_last_use(self):
        identity = 'fn identity(x:&mut Int)->&mut Int{return x;}'
        relay = 'fn relay(x:&mut Int)->&mut Int{return identity(x);}'
        prefix = identity + relay + PREFIX
        result = self.run_source(prefix + match.match_arm(
            'let mut child=relay(r);child.set(20);print(child);r.set(30);') +
            'print(w);print(n);')
        self.assertEqual(result.stdout, '20\nW.Bound(30)\n30\n')
        for premature in ('r.set(30);', 'print(r);', 'edit(r);'):
            self.reject(prefix + match.match_arm(
                'let mut child=relay(r);' + premature + 'print(child);'), 'emprunt actif')
        self.reject(prefix + match.match_arm('let mut child=relay(r);print(child);') +
                    'print(child);', 'inconnue')
        self.reject(prefix + match.match_arm('let mut child=relay(r);print(child);print(n);'),
                    'emprunt actif')

    def test_returned_mutable_reborrow_in_impossible_arm(self):
        decl = 'enum W{Bound{data:&mut Int},Other{data:&mut Int}}'
        identity = 'fn identity(x:&mut Int)->&mut Int{return x;}'
        source = identity + decl + match.SETUP + match.HOLDER
        result = self.run_source(source +
            'match &mut w{W.Bound{data:r}=>{let mut child=identity(r);child.set(30);},'
            'W.Other{data:r}=>{let mut child=identity(r);address(child);child.set(40);}}print(n);')
        self.assertEqual(result.stdout, '30\n')
