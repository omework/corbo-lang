"""Fault injection for opaque borrowed-result lifetime and access contracts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('result_groups_erased', [('results.py',
        'fields += tuple((key, frozenset(targets)) for key, targets in result_fields.items())\n        if result_mode in ASYNC_CAPTURE_VIEW_MODES:',
        'fields += ()\n        if result_mode in ASYNC_CAPTURE_VIEW_MODES:')], 'test_opaque_caller_has_no_function_bodies',
        ('Error not raised','capture empruntée introuvable','retour sans provenance')),
    ('all_captures_retained_after_join', [('async_lowering.py',
        'for index in node.public_result_borrows)', 'for index in (1, 2, 3, *node.public_result_borrows))'),
        ('crust.py', 'for index in self.async_definitions[nominal][0].public_result_borrows)',
        'for index in (1, 2, 3, *self.async_definitions[nominal][0].public_result_borrows))')],
        'test_relay_join_helper_mutability_cleanup_and_failure', ('emprunt','capture','survit')),
    ('result_projection_lost_at_conversion', [('crust.py',
        'allocation.dependencies += tuple((key, tuple(targets.values())) for key, targets in grouped.items())',
        'allocation.dependencies += ()')], 'test_initial_counterexample',
        ('capture empruntée introuvable','référence','cible','retour sans provenance')),
    ('mutable_ancestor_erased', [('crust.py',
        "result_dependencies = tuple((('mut.5' if key.startswith('mut.') else 'ref.4')", "result_dependencies = tuple(('ref.4'")],
        'test_shared_result_from_mutable_capture_keeps_ancestor', ('Error not raised',)),
    ('symbolic_byte_result_as_allocation', [('crust.py',
        "if capture in ASYNC_CAPTURE_VIEW_MODES or (capture, capture_type) == ('mut', 'u8'):",
        'if capture in ASYNC_CAPTURE_VIEW_MODES:')], 'test_byte_join_helper_returns_inline_reference',
        ('exige des cibles Int',)),
    ('vector_index_storage_erased', [('constraints.py',
        "projection_assets=values[0].all_assets if op == 'array_index' else frozenset()",
        'projection_assets=frozenset()')], 'test_mutable_byte_result_and_payload_mismatch',
        ('attend une allocation u8',)),
)

def main():
    success=True
    for name,edits,method,diagnostics in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-borrowed-handles-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            for filename,before,after in edits:
                path=target/filename;original=path.read_text()
                assert original.count(before)==1,(name,original.count(before))
                path.write_text(original.replace(before,after))
            script=f'''import sys,unittest
sys.path[:0]=[{directory!r},{str(ROOT/'tests')!r}]
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
'test_public_borrowed_handles.PublicBorrowedHandleTests.{method}'))
sys.exit(not result.wasSuccessful())'''
            result=subprocess.run([sys.executable,'-c',script],cwd=directory,capture_output=True,text=True,timeout=120)
        detected=result.returncode==1 and any(message in result.stderr for message in diagnostics)
        print(name,'DETECTED' if detected else 'SURVIVED' if result.returncode==0 else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True);success &= detected
    return int(not success)

if __name__=='__main__':sys.exit(main())
