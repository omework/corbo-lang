"""Check cleanup ownership and provenance faults in isolated compiler copies."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
root = Path(__file__).resolve().parents[1]
mutations = (
    ('conserve la garde de l’ancienne entrée', 'if state[\'guard\']:\n                        code.append',
     'if False and state[\'guard\']:\n                        code.append', 'test_moved_sibling_does_not_keep_a_second_cleanup'),
    ('perd une provenance possible', "scope.id, name, source_union(*(state['sources'] for state in states)),",
     "scope.id, name, states[0]['sources'],", 'test_return_contract_keeps_both_pools_and_reset_checks_them'),
)
report = []
for name, original, mutant, test in mutations:
    with tempfile.TemporaryDirectory(prefix='crust-ancestor-mutation-') as directory:
        work = Path(directory)
        (work / 'tests').mkdir()
        shutil.copytree(root / 'prototype', work / 'prototype',
                        ignore=shutil.ignore_patterns('__pycache__'))
        for file in ('tests/test_crust.py','tests/test_ancestor_join.py'):
            shutil.copyfile(root / file, work / file)
        compiler = work / 'prototype' / 'crust.py'
        source = compiler.read_text()
        assert source.count(original) == 1
        compiler.write_text(source.replace(original, mutant))
        run = subprocess.run([sys.executable, '-E', '-m', 'unittest', f'test_ancestor_join.AncestorJoinTests.{test}'],
                             cwd=work / 'tests', capture_output=True, text=True, timeout=30)
        report.append(dict(mutation=name, test=test, status='detected' if run.returncode else 'survived',
                           evidence=run.stderr.splitlines()[-9:]))
print(json.dumps(report, indent=2, ensure_ascii=False))
