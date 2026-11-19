"""Challenge descendant provenance, native typing and prepared cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('forget_concrete_descendant_pool','crust.py',
     'source_union(target.sources, self.owned_sources(target)) for target in transferred',
     'target.sources for target in transferred',
     'test_nested_graph_source_model'),
    ('forget_symbolic_descendant_pool','results.py',
     'task_sources.update(self.owned_capture_storage(value, field))',
     'pass',
     'test_factory_contract_keeps_descendant_source'),
    ('lose_instantiated_descendant_pool','crust.py',
     "        if symbol.kind == 'allocation_field_parameter':\n            return source_union(*(child.sources for carrier in binding.referents or (binding.alloc,)",
     "        if symbol.kind == 'allocation_field_parameter':\n            return ()\n            return source_union(*(child.sources for carrier in binding.referents or (binding.alloc,)",
     'test_nested_graph_source_model'),
    ('reject_native_owned_field','native_threads.py',
     "if signature in (('ref', 'Int'), ('mut', 'Int'), ('owned', 'Int')):",
     "if signature in (('ref', 'Int'), ('mut', 'Int')):",
     'test_native_thread_whole_capture'),
    ('forget_prepared_owner','async_lowering.py',
     'for _, cells, _ in reversed(pending_capture_groups):',
     'for _, cells, _ in ():',
     'test_identity_and_cleanup_at_each_task_state'),
)


def main():
    suite='test_async_owned_struct_captures.AsyncOwnedStructCaptureTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-owned-struct-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            assert original.count(before)==1,(name,original.count(before))
            path.write_text(original.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and ('AssertionError' in result.stderr or
            "crust.Error:" in result.stderr) and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and
            'internal error:' not in result.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
