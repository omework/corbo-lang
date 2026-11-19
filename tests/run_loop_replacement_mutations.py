"""Exercise iteration-pointer and retired-import faults in isolated copies."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = (
    ('omission de la mise à jour du pointeur',
     "edit.append(f'{c} = {candidate.c};')", 'pass',
     'test_continue_and_fallthrough_preserve_slot_identity'),
    ('restauration de l’ancien accès importé',
     'row[5].pop(allocation.id, None)', 'pass',
     'test_imported_old_handle_does_not_revive_on_scope_exit'),
    ('refus systématique des champs empruntés',
     '(holder is selected or holder.id in transfers)',
     'holder.scope in {active.id for active in self.scopes}',
     'test_unused_reference_field_does_not_block_reentry'),
)


def run_mutations():
    report = []
    for name, before, after, test in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix='crust-carry-mutation-') as directory:
            work = Path(directory)
            (work / 'tests').mkdir()
            shutil.copytree(ROOT / 'prototype', work / 'prototype',
                            ignore=shutil.ignore_patterns('__pycache__'))
            for file in ('tests/test_crust.py', 'tests/test_loop_replacements.py'):
                shutil.copyfile(ROOT / file, work / file)
            compiler = work / 'prototype' / 'crust.py'
            original = compiler.read_text()
            assert before in original
            compiler.write_text(original.replace(before, after))
            result = subprocess.run(
                [sys.executable, '-E', '-m', 'unittest', f'test_loop_replacements.LoopReplacementTests.{test}'],
                cwd=work / 'tests', capture_output=True, text=True, timeout=40)
            report.append(dict(mutation=name, test=test,
                               status='detected' if result.returncode else 'survived',
                               evidence=result.stderr.splitlines()[-15:]))
    return report


if __name__ == '__main__':
    print(json.dumps(run_mutations(), ensure_ascii=False, indent=2))
