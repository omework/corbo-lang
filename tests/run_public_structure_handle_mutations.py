"""Faults in structure payload erasure, root storage and returned loans."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('erase_result_field_contract', 'results.py',
     "if result_mode in ('owned', 'join_owned'):", 'if False:',
     'test_public_parameter_relays_preserve_returned_loan'),
    ('erase_concrete_result_fields', 'crust.py',
     "if mode in ('owned', 'join_owned'):\n            projected, parents = self.project_task_result_fields",
     'if False:\n            projected, parents = self.project_task_result_fields',
     'test_annotation_keeps_local_and_pool_distinct'),
    ('erase_public_descriptor_fields', 'handle_types.py',
     'borrowed_fields=fields)', 'borrowed_fields=())',
     'test_public_parameter_relays_preserve_returned_loan'),
    ('drop_post_wait_field_loans', 'async_lowering.py',
     "or f'{position}/{selected_field}' in result_field_selectors", 'or False',
     'test_factory_from_owned_structure_argument'),
    ('forget_local_task_argument', 'async_lowering.py',
     "if any(target in implicit_stacks for target, access in record[4] if access == 'storage'):", 'if False:',
     'test_recorded_local_structure_and_returned_loan'),
    ('forget_public_storage_obligation', 'storage_requirements.py',
     "if (kind := public_storage(typ, structures)) is not None:\n            require(context, value, kind, line)",
     "if (kind := public_storage(typ, structures)) is not None:\n            pass",
     'test_factory_contract_checks_storage_even_if_caller_drops_result'),
    ('forget_previous_branch_storage', 'crust.py',
     "task_result_sources=source_union(*(state['task_result_sources']\n                                                  for state in selected_item_states))",
     'task_result_sources=()', 'test_two_routine_types_share_a_public_structure_result'),
)


def main():
    suite = 'test_public_structure_handles.PublicStructureHandleTests'
    baseline = run(ROOT, suite)
    print('BASELINE', baseline.returncode, baseline.stdout+baseline.stderr, flush=True)
    if baseline.returncode:
        return 1
    success = True
    for name, filename, before, after, method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-public-structure-') as directory:
            target = Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target/path.name)
            path = target/filename
            source = path.read_text()
            assert source.count(before) == 1, (name, source.count(before))
            path.write_text(source.replace(before, after))
            result = run(target, suite+'.'+method)
        detected = result.returncode == 1 and 'AssertionError' in result.stderr
        print(name, 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE', flush=True)
        print(result.stdout+result.stderr, flush=True)
        success &= detected
    return int(not success)


if __name__ == '__main__':sys.exit(main())
