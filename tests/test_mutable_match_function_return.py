"""Returned match projections reserve an enum parameter in the caller."""
from functools import partial, update_wrapper
import unittest

from crust import verify_program

# These regressions exercise the historical reset profile.
verify_program = update_wrapper(partial(verify_program, allow_legacy_reset=True), verify_program)
import test_mutable_match as match
from test_mutable_match_escape import IDENTITY, MATCH

OPEN = 'fn open(w:&mut W)->&mut Int{' + MATCH + 'return out;}'
PREFIX = IDENTITY + OPEN + match.PREFIX + 'let mut out=open(&mut w);'


class MutableMatchFunctionReturnTests(unittest.TestCase):
    execute = match.MutableMatchTests.execute
    with_source = match.MutableMatchTests.with_source
    run_source = match.MutableMatchTests.run_source
    reject = match.MutableMatchTests.reject

    def test_caller_recovers_writer_after_last_use(self):
        self.reject(PREFIX + 'print(w);out.set(30);', 'emprunt actif')
        result = self.run_source(PREFIX + 'out.set(30);print(w);print(n);')
        self.assertEqual(result.stdout, 'W.Bound(30)\n30\n')
        self.assertEqual([line for line in result.stderr.splitlines() if line.startswith('destroy ')],
                         ['destroy w=W.Bound', 'destroy n=30'])

    def test_contract_names_field_and_parameter(self):
        contract = verify_program(PREFIX + 'out.set(30);').function_contracts['open']
        self.assertEqual({(target.kind, target.parameter, target.field)
                          for target in contract.result.reference_targets},
                         {('field_parameter', 0, 'Bound.data')})

    def test_writer_and_target_cannot_be_destroyed_early(self):
        for operation in ('drop(->w);', 'drop(->n);', 'q.reset();', 'p.reset();'):
            with self.subTest(operation=operation):
                self.reject(PREFIX + operation + 'out.set(30);', 'emprunt|reset')
        result = self.run_source(PREFIX + 'out.set(30);q.reset();p.reset();')
        self.assertEqual(result.stderr.count('destroy w=W.Bound'), 1)
        self.assertEqual(result.stderr.count('destroy n=30'), 1)

    def test_relay_renumbers_the_holder_parameter(self):
        relay = 'fn relay(unused:Int,owner:&mut W)->&mut Int{return identity(open(owner));}'
        prefix = IDENTITY + OPEN + relay + match.PREFIX + 'let mut out=relay(0,&mut w);'
        self.reject(prefix + 'print(w);out.set(30);', 'emprunt actif')
        self.assertEqual(self.run_source(prefix + 'out.set(30);print(w);').stdout,
                         'W.Bound(30)\n')

    def test_multiple_variants_only_use_present_fields(self):
        decl = 'enum W{Bound{data:&mut Int},Other{data:&mut Int}}'
        open_both = ('fn open(w:&mut W)->&mut Int{let mut out=match &mut w{'
                     'W.Bound{data:r}=>{r},W.Other{data:r}=>{r}};return out;}')
        for variant in ('Bound', 'Other'):
            with self.subTest(variant=variant):
                source = decl + open_both + match.SETUP + match.HOLDER.replace('W.Bound', f'W.{variant}')
                source += 'let mut out=open(&mut w);'
                self.reject(source + 'print(w);out.set(30);', 'emprunt actif')
                self.assertEqual(self.run_source(source + 'out.set(30);print(w);').stdout,
                                 f'W.{variant}(30)\n')

    def test_owned_parameter_is_not_durable_at_return(self):
        owned = 'fn bad(mut w:->W)->&mut Int{' + MATCH + 'return out;}'
        self.reject(match.DECL + IDENTITY + owned, 'non durable')
