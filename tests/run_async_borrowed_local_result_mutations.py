"""Corrupt carrier result flow in temporary copies; keep the oracles intact."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('forget_completed_borrowed_fields', 'async_result_storage.py',
     '    return effect.completion_result.borrowed_fields', '    return ()',
     'test_recorded_and_target_lifetime'),
    ('forget_async_field_loans', 'async_lowering.py',
     "active_loans[('stored_field', holder, tuple(field.lstrip('.').split('.')))] = list(dict.fromkeys(held))",
     "active_loans[('stored_field', holder, tuple(field.lstrip('.').split('.')))] = []",
     'test_direct_await_named_and_launched'),
    ('forget_extracted_payload_loans', 'crust.py',
     '            allocation.dependencies = prototype.dependencies',
     '            allocation.dependencies = ()', 'test_recorded_and_target_lifetime'),
    ('forget_symbolic_payload_loans', 'results.py',
     "return flow, replace(values[0], mode='owned', absent_owned_payload=False)",
     "return flow, replace(values[0], mode='owned', fields=(), absent_owned_payload=False)",
     'test_helper_chain_keeps_both_possible_targets'),
    ('forget_helper_capture_targets', 'crust.py',
     '                    resolved.extend(root for _, roots in captures for root in roots)',
     '                    pass # discarded captured targets', 'test_join_returned_by_sync_helper'),
    ('leak_unused_fallback_slot', 'crust.py',
     "self.lines.append(f'local_reservation_end({local_result_reservation});')",
     "self.lines.append('/* missing fallback slot release */')", 'test_join_returned_by_sync_helper'),
    ('forget_task_local_storage', 'crust.py',
     "if completed and completed.candidates and all(\n                            candidate.kind == 'fresh'",
     "if False and completed and completed.candidates and all(\n                            candidate.kind == 'fresh'",
     'test_helper_chain_keeps_both_possible_targets'),
    ('forget_awaited_carrier_transport', 'async_lowering.py',
     '                move_stored_fields(task, result)',
     '                pass # missing awaited carrier transport', 'test_direct_await_named_and_launched'),
    ('destroy_borrowed_target', 'async_lowering.py',
     "else 1 if field_type.startswith('&') else 0)",
     "else 2 if field_type.startswith('&') else 0)", 'test_suspended_cleanup_and_identity'),
)


def main():
    suite = 'test_async_borrowed_local_results.AsyncBorrowedLocalResultTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout + baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-borrowed-result-mutant-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            path = target / filename
            source = path.read_text()
            assert source.count(before) == 1, (name, source.count(before))
            path.write_text(source.replace(before, after))
            result = run(target, suite + '.' + method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout + result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':
    sys.exit(main())
