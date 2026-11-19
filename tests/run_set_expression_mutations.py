"""Counterexamples for computed writes, applied only to compiler copies."""
from pathlib import Path
import shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('write_permission_lost','crust.py',
  "self.access(binding, write=True, after=True)\n                    destination = binding.c",
  "pass\n                    destination = binding.c",'test_calls_order_identity_and_last_borrow_use',
  ('Error not raised',)),
 ('rhs_not_evaluated','crust.py',
  "kind, value, _ = self.expression(args[1], scope, 'set')",
  "kind, value = 'scalar', '0'",'test_independent_integer_sequence_model',('AssertionError:',)),
 ('rhs_effects_lost','effects.py',
  "part = self.expression(args[1], environment, resets, allocations, pools, line,\n                                       break_types=break_types)",
  "part = {'next'}",'test_effects_inside_rhs_propagate_through_opaque_calls',
  ('Error not raised','AssertionError:','invariant')),
)

def main():
    success=True
    for name,filename,before,after,method,diagnostics in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-set-expression-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename;text=path.read_text()
            assert text.count(before)==1,(name,text.count(before))
            path.write_text(text.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_set_expressions.SetExpressionTests.{method}'))
sys.exit(not r.wasSuccessful())'''
            result=subprocess.run([sys.executable,'-c',script],cwd=directory,capture_output=True,text=True,timeout=120)
        detected=result.returncode==1 and any(d in result.stderr for d in diagnostics)
        print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True);success &= detected
    return int(not success)
if __name__=='__main__':sys.exit(main())
