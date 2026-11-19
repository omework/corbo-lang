from pathlib import Path
import sys,unittest
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root / 'prototype'),str(root/'tests')]
from test_async_owned_borrowed_captures import OwnedBorrowedCaptureTests as Tests
counts={'native':0,'invalid_programs':0,'rejection_checks':0}
original_run=Tests.run_c_oracle;original_refused=Tests.refused
def run(self,*args,**kw):
 result=original_run(self,*args,**kw);counts['native']+=1;return result
def refused(self,*args,**kw):
 counts['invalid_programs']+=1;counts['rejection_checks']+=2;return original_refused(self,*args,**kw)
Tests.run_c_oracle=run;Tests.refused=refused
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
print(counts,flush=True);sys.exit(not result.wasSuccessful())
