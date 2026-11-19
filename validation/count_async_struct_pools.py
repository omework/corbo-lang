"""Count only executions and refusals actually reached by the targeted suite."""
import sys
from pathlib import Path
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1] / 'prototype'),str(Path(__file__).resolve().parents[1]/'tests')]
from test_async_struct_pools import AsyncStructPoolTests as Tests
counts={'native':0,'invalid_programs':0,'rejection_checks':0}
original_run=Tests.run_c_oracle
original_refused=Tests.refused
def run(self,*a,**kw):
    result=original_run(self,*a,**kw);counts['native']+=1;return result
def refused(self,*a,**kw):
    counts['invalid_programs']+=1;counts['rejection_checks']+=2;return original_refused(self,*a,**kw)
Tests.run_c_oracle=run
Tests.refused=refused
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
print(counts,flush=True)
sys.exit(not result.wasSuccessful())
