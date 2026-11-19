"""Arm-local exclusive projections and the lifetime of their holder."""
import unittest

import test_mutable_reference_fields as fields

DECL, SETUP, HOLDER = fields.DECL, fields.SETUP, fields.HOLDER
PREFIX = DECL + SETUP + HOLDER


def match_arm(body, subject='w', mode='&mut '):
    return f'match {mode}{subject}{{W.Bound{{data:r}}=>{{{body}}}}}'


class MutableMatchTests(unittest.TestCase):
    execute = fields.MutableReferenceFieldTests.execute
    with_source = fields.MutableReferenceFieldTests.with_source
    reject = fields.MutableReferenceFieldTests.reject
    run_source = fields.MutableReferenceFieldTests.run_source

    def test_payload_identity_and_cleanup(self):
        result = self.run_source(PREFIX + 'address(w);' +
                                 match_arm('{address(r);r.set(20);}') +
                                 'address(w);print(w);address(n);print(n);')
        holder_before, projected, holder_after, holder, target, value = result.stdout.splitlines()
        self.assertEqual(holder_before, holder_after)
        self.assertEqual(projected, target)
        self.assertEqual((holder, value), ('W.Bound(20)', '20'))
        self.assertEqual([line for line in result.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy w=W.Bound', 'destroy n=20'])

    def test_lifetime_boundaries(self):
        # The target stays reserved throughout the arm and until the last
        # holder use. Only reads placed beyond both boundaries may succeed.
        cases = [
            ('print(n);r.set(20);', '', False),
            ('r.set(20);print(n);', '', False),
            ('', 'print(n);', True),
            ('r.set(20);', 'print(n);print(w);', False),
            ('r.set(20);', 'print(w);print(n);', True),
            ('r.set(20);', 'print(n);', True),
        ]
        for arm, tail, allowed in cases:
            with self.subTest(arm=arm, tail=tail):
                source = PREFIX + match_arm(arm) + tail
                if allowed:
                    self.assertEqual(self.run_source(source).stdout.splitlines()[-1],
                                     '20' if 'set' in arm else '10')
                else:
                    self.reject(source, 'emprunt actif')

    def test_holder_cannot_be_accessed_inside_arm(self):
        self.reject(PREFIX + match_arm('r.set(20);print(w);'), 'emprunt actif')

    def test_match_requires_exclusive_access(self):
        self.reject(DECL + SETUP + HOLDER.replace('let mut w', 'let w') +
                    match_arm('r.set(20);'), 'immuable')
        self.reject(PREFIX + 'let a=&w;' + match_arm('r.set(20);', 'a'), 'lecture')
        self.reject(PREFIX + 'let a=&w;' + match_arm('r.set(20);') + 'print(a);', 'emprunt actif')
        self.reject(PREFIX + match_arm('r.set(20);', mode='&'), 'lecture uniquement')

    def test_arm_local_and_only_projected_writes(self):
        self.reject(PREFIX + match_arm('r.set(20);') + 'print(r);', 'inconnue')
        for body in ('n.set(20);', 'let mut r=1;r.set(20);', 'p.reset();',
                     'drop(->w);', 'let a=&mut r;'):
            with self.subTest(body=body):
                self.reject(PREFIX + match_arm(body), 'match mutable')

    def test_mixed_modes(self):
        prefix = ('enum M{A{x:&mut Int,y:&Int,z:Int}}'
                  'let mut p=pool<Int>(2);let mut q=pool<M>(1);'
                  'let mut n=new(p)Int(10);let y=new(p)Int(30);'
                  'let mut w=new(q)M.A{x:&mut n,y:&y,z:40};')
        arm = 'match &mut w{M.A{x:r,y:s,z:t}=>{%s}}'
        result = self.run_source(prefix + arm % 'r.set(20);print(s);print(t);' + 'print(w);')
        self.assertEqual(result.stdout, '30\n40\nM.A(20, 30, 40)\n')
        for operation in ('s.set(20);', 't.set(20);'):
            self.reject(prefix + arm % operation, 'champ &mut Int')

    def test_transfer_function_reborrow_and_reset(self):
        functions = (fields.MAKE + 'fn edit(w:&mut W){' + match_arm('r.set(20);') + '}'
                     'fn forward(w:&mut W){edit(w);}')
        source = DECL + functions + SETUP + 'let mut w=make(&mut q,&mut n);forward(&mut w);'
        self.reject(source + 'p.reset();print(w);', 'reset')
        self.reject(source + 'drop(->n);print(w);', 'emprunt')
        result = self.run_source(source + 'print(w);p.reset();q.reset();')
        self.assertEqual(result.stdout, 'W.Bound(20)\n')
        self.assertEqual(result.stderr.count('destroy n=20'), 1)
        self.assertEqual(result.stderr.count('destroy w=W.Bound'), 1)

    def test_unreachable_variant_still_typechecks(self):
        source = PREFIX.replace('Bound{data:&mut Int}', 'Bound{data:&mut Int},Other{data:&mut Int}')
        result = self.run_source(source +
                                 'match &mut w{W.Bound{data:r}=>{r.set(20);},'
                                 'W.Other{data:r}=>{r.set(30);}}print(n);')
        self.assertEqual(result.stdout, '20\n')

    def test_two_disjoint_exclusive_fields(self):
        result = self.run_source('enum W{A{x:&mut Int,y:&mut Int}}'
                                 'let mut p=pool<Int>(2);let mut q=pool<W>(1);'
                                 'let mut n=new(p)Int(10);let mut m=new(p)Int(11);'
                                 'let mut w=new(q)W.A{x:&mut n,y:&mut m};'
                                 'match &mut w{W.A{x:r,y:s}=>{r.set(20);s.set(21);}}'
                                 'print(w);print(n);print(m);')
        self.assertEqual(result.stdout, 'W.A(20, 21)\n20\n21\n')

    def test_conditional_field_targets_are_conservative(self):
        source = """
            enum W{A{x:&mut Int,y:&mut Int}}
            fn make(q:&mut Pool<W>,a:&mut Int,b:&mut Int,k:Int)-><-W{
                if k==0 {let w=new(q)W.A{x:a,y:b};return<-w;}
                let w=new(q)W.A{x:b,y:a};return<-w;
            }
            let mut p=pool<Int>(2);let mut q=pool<W>(1);
            let mut a=new(p)Int(10);let mut b=new(p)Int(11);
            let mut w=make(&mut q,&mut a,&mut b,0);
        """
        self.reject(source + 'match &mut w{W.A{x:r,y:s}=>{r.set(20);s.set(21);}}',
                    'cibles possibles.*aliasées')
        result = self.run_source(source + 'match &mut w{W.A{x:r,y:_}=>{r.set(20);}}print(w);')
        self.assertEqual(result.stdout, 'W.A(20, 11)\n')
