"""Field dereferences remain ordinary reads in a shared enum match."""
from pathlib import Path
import unittest
import test_select_source as sources

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'validation/open-shared-enum-descendant-read.crb').read_text()


class SharedMatchFieldReadTests(unittest.TestCase):
    run_source=sources.SelectSourceTests.run_source
    run_c_oracle=sources.SelectSourceTests.run_c_oracle
    refused=sources.SelectSourceTests.refused

    def test_direct_local_and_arithmetic_reads(self):
        for expression,expected in (('*i.view',7),
                                    ('let n=*i.view;n',7),
                                    ('let n=*i.view+2;n+1',10)):
            with self.subTest(expression=expression):
                source=BASE.replace('=>{*i.view}', '=>{'+expression+'}')
                self.assertEqual(self.run_source(source).stdout,str(expected)+'\n')

    def test_scalar_result_outlives_carrier_and_target(self):
        source=BASE.replace('print(read(&o));',
                            'let result=read(&o);drop(->o);drop(->n);print(result);')
        self.assertEqual(self.run_source(source).stdout,'7\n')

    def test_missing_field_is_still_rejected(self):
        self.refused(BASE.replace('*i.view','*i.missing'),'champ|inconnu')


if __name__=='__main__':unittest.main()
