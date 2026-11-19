"""Lose result provenance or completion writes in temporary compiler copies."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
    ('erase_owned_candidates','async_structure_effects.py',
     'value = merge_owned_values(values)',
     'value = replace(merge_owned_values(values), candidates=frozenset())',
     'test_owned_result_return_and_pool_provenance'),
    ('keep_only_first_winner_origin','async_structure_effects.py',
     'value = merge_owned_values(values)',
     'value = merge_owned_values(values[:1])',
     'test_independent_owned_winner_and_reuse_model'),
    ('erase_returned_view_targets','async_structure_effects.py',
     'value = merge_owned_values(values)',
     'value = replace(merge_owned_values(values), reference_targets=frozenset())',
     'test_returned_view_contract_through_direct_relay'),
    ('forget_owned_completion_writes','async_structure_effects.py',
     'self.results.summaries[symbol] = result',
     "self.results.summaries[symbol] = replace(result, structure_fields=()) if result.mode == 'owned' else result",
     'test_completed_owned_winner_publishes_field'),
    ('exclude_owned_returning_parent','async_lowering.py',
     'or result[0] not in FIELD_RESULT_MODES):',
     "or result[0] == 'owned' or result[0] not in FIELD_RESULT_MODES):",
     'test_owned_result_return_and_pool_provenance'),
)


def main():
    suite='test_select_results.SelectResultsTests'
    baseline=run(ROOT,suite)
    print('BASELINE','PASS' if baseline.returncode==0 else 'INCONCLUSIVE',flush=True)
    print(baseline.stdout+baseline.stderr,flush=True)
    if baseline.returncode:return 1
    success=True
    for name,filename,before,after,method in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-select-results-') as directory:
            target=Path(directory)
            for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
            path=target/filename
            original=path.read_text()
            # The backend has the same guard for direct and synchronous child calls.
            expected=2 if name=='exclude_owned_returning_parent' else 1
            assert original.count(before)==expected,(name,original.count(before))
            path.write_text(original.replace(before,after))
            result=run(target,suite+'.'+method)
        detected=result.returncode==1 and 'AssertionError' in result.stderr and not (
            'error:' in result.stderr and 'runtime error:' not in result.stderr and 'internal error:' not in result.stderr)
        print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
        print(result.stdout+result.stderr,flush=True)
        success &= detected
    return int(not success)


if __name__=='__main__':sys.exit(main())
