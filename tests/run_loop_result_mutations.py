"""Exercise four narrowly targeted faults in temporary copies."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
mutants = [
    ('retient le candidat dans son scope', '            allocation.alive = allocation.definite = False\n        elif kind',
     '            pass\n        elif kind', 'test_two_transfers_preserve_identity_and_cleanup_order'),
    ('omet la vérification de la cible sur break', '            self.check_reference_destination(allocation, destination)\n            if expr',
     '            pass\n            if expr', 'test_each_transfer_checks_storage_and_borrow_target'),
    ('donne priorité à un trou', 'source->pool && at_limit && source->free_head != NULL',
     'source->pool && source->free_head != NULL', 'test_cursor_first_then_hole_then_group_reset'),
    ('récupère les slots avant la fin des destructeurs du reset',
     '    } else if (!(resetting && source->pool)) {', '    } else if (!(resetting && source->pool && 0)) {',
     'test_cursor_first_then_hole_then_group_reset'),
]
out = []
for name, before, after, test in mutants:
    with tempfile.TemporaryDirectory(prefix='crust-loop-mut-') as tmp:
        work = Path(tmp)
        tests = work / 'tests'
        tests.mkdir()
        shutil.copytree(root / 'prototype', work / 'prototype',
                        ignore=shutil.ignore_patterns('__pycache__'))
        for source in ('tests/test_crust.py', 'tests/test_loop_results.py'):
            shutil.copyfile(root / source, work / source)
        compiler = work / 'prototype' / 'crust.py'
        original = compiler.read_text()
        assert original.count(before) == 1, name
        compiler.write_text(original.replace(before, after))
        result = subprocess.run([sys.executable, '-E', '-m', 'unittest',
                                 'test_loop_results.LoopResultTests.' + test], cwd=tests,
                                capture_output=True, text=True, timeout=40)
        out.append({'mutation': name, 'test': test, 'status': 'detected' if result.returncode else 'survived',
                    'log': result.stderr})
print(json.dumps(out, ensure_ascii=False, indent=2))
