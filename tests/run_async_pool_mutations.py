"""Source-reservation/provenance faults; unchanged tests in temporary compilers."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('allocation_nominal_type_erased', 'async_lowering.py',
     "if pool_type != f'Pool<{typ}>' or (typ != 'Int' and expr[4:] != ('pool_default',)):",
     'if False: # erase the explicit allocation type',
     'test_pool_mode_type_and_explicit_reference'),
    ('caller_pool_not_reserved', 'crust.py',
     "if task.alive and task.typ.startswith(('Task<', 'Execution<')):",
     'if False: # forget live task source loans',
     'test_pool_reserved_before_spawn_until_join'),
    ('named_source_loan_ignored', 'crust.py',
     'and other.source_borrowed and other.valid and not other.suspended',
     'and False and other.valid and not other.suspended',
     'test_named_pool_loan_ends_at_last_use_and_shared_loans_coexist'),
    ('shared_pool_upgraded', 'async_lowering.py',
     "if mode == 'mut' and references[name] != 'mut':",
     'if False: # permit writes through a shared pool reference',
     'test_pool_mode_type_and_explicit_reference'),
    ('child_pool_loan_omitted', 'async_lowering.py',
     "if (mode, typ) in pool_sync_types:\n                    value, held = pool_argument(argument, mode, typ, line)\n                    loans.extend(held)\n                elif mode == 'scalar':",
     "if (mode, typ) in pool_sync_types:\n                    value, held = pool_argument(argument, mode, typ, line)\n                elif mode == 'scalar':",
     'test_child_keeps_pool_reserved_until_await'),
    ('fresh_result_contract_ignored', 'async_lowering.py',
     "and candidate.source.kind == 'source_parameter' else None)",
     'and False else None)',
     'test_precise_result_pool_survives_while_other_capture_pool_closes'),
    ('native_source_binding_reusable', 'crust.py',
     'if node.native_block:\n                        binding.valid = False\n                    continue',
     'if node.native_block:\n                        pass # capture leaves original source binding usable\n                    continue',
     'test_native_block_transfers_pool_reference_binding'),
]


def run(folder, test):
    script = f'''import sys,unittest,json
sys.path[:0]=[{str(folder)!r},{str(ROOT/'tests')!r}]
import test_async_pool_injection as m
counts={{'native_executions':0,'accepted_check_only':0,'rejected_programs':0}}
native=m.AsyncPoolInjectionTests.run_native
def counted_native(self,*a,**kw):
    result=native(self,*a,**kw)
    counts['native_executions']+=1
    return result
m.AsyncPoolInjectionTests.run_native=counted_native
verify=m.verify_program
def counted_verify(*a,**kw):
    try: result=verify(*a,**kw)
    except m.Error:
        counts['rejected_programs']+=1
        raise
    counts['accepted_check_only']+=1
    return result
m.verify_program=counted_verify
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName({test!r}))
print(json.dumps(counts))
sys.exit(not r.wasSuccessful())
'''
    return subprocess.run([sys.executable, '-c', script], cwd=folder, capture_output=True,
                          text=True, timeout=150)


def main():
    baseline = run(ROOT, 'test_async_pool_injection')
    print('BASELINE', 'PASS' if baseline.returncode == 0 else 'INCONCLUSIVE', flush=True)
    print(baseline.stdout+baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, test in MUTATIONS:
        source = (ROOT / 'prototype'/filename).read_text()
        if source.count(before) != 1:
            raise SystemExit(f'{name}: anchor count {source.count(before)}')
        with tempfile.TemporaryDirectory(prefix='crust-async-pool-mut-') as folder:
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, Path(folder)/path.name)
            (Path(folder)/filename).write_text(source.replace(before, after))
            result = run(folder, 'test_async_pool_injection.AsyncPoolInjectionTests.'+test)
            semantic_error = 'crust.Error:' in result.stderr and 'ERROR:' in result.stderr
            detected = result.returncode == 1 and ('FAIL:' in result.stderr or semantic_error)
            print(name, 'DETECTED' if detected else 'SURVIVED' if result.returncode == 0 else 'INCONCLUSIVE', flush=True)
            print(result.stdout+result.stderr[-5000:], flush=True)
            success &= detected
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
