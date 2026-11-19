"""Inject pool-contract faults in temporary copies; never mutate the checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('omit_signature_requirement', 'effects.py',
     "                    pools.add((index, typ[5:-1]))", "                    pass",
     'test_unused_typed_signature_requires_pool_even_with_empty_body'),
    ('omit_transitive_requirement', 'effects.py',
     '            self.require_pool(actual_sources[index], typ, allocations, pools, line)', '            pass',
     'test_generated_call_graphs_against_independent_route_model'),
    ('wrong_argument_substitution', 'effects.py',
     'self.require_pool(actual_sources[index], typ, allocations, pools, line)',
     'self.require_pool(actual_sources[next(iter(actual_sources))], typ, allocations, pools, line)',
     'test_multilevel_parameter_reordering'),
    ('omit_opaque_call_check', 'crust.py',
     "            if not source.supports_pool(typ):\n                self.fail(f\"source incompatible :",
     "            if False and not source.supports_pool(typ):\n                self.fail(f\"source incompatible :",
     'test_opaque_contract_checks_without_body_catalog_or_inference_maps'),
    ('reject_matching_pool', 'crust.py',
     "            if not source.supports_pool(typ):\n                self.fail(f\"source incompatible :",
     "            if source.supports_pool(typ):\n                self.fail(f\"source incompatible :",
     'test_minimally_different_correct_pool_accepted_and_executed'),
]


def fingerprint():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted([*(ROOT / 'prototype').glob('*.py'), *ROOT.joinpath('tests').glob('*.py')])}


def run(folder, selected):
    command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_pool_requirements.py', '-q']
    if selected:
        command.extend(['-k', selected])
    try:
        result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired:
        return {'status': 'inconclusive', 'reason': 'test timeout'}
    output = result.stdout + result.stderr
    infrastructure = any(word in output for word in ('SyntaxError', 'ImportError', 'Failed to import test module'))
    status = ('inconclusive' if infrastructure or 'Ran ' not in output else
              'survived' if result.returncode == 0 else 'detected')
    return {'status': status, 'returncode': result.returncode, 'output': output[-3500:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    before = fingerprint()
    report = {'scope': 'five selected static pool-contract faults; no global mutation rate',
              'sanitizer_environment': os.environ.get('CRUST_SANITIZE'), 'mutations': []}
    with tempfile.TemporaryDirectory(prefix='crust-pool-mutations-') as directory:
        folder = Path(directory)
        for path in (ROOT / 'prototype').glob('*.py'):
            shutil.copy2(path, folder / path.name)
        shutil.copytree(ROOT / 'tests', folder / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
        baseline = run(folder, None)
        report['baseline'] = baseline
        if baseline.get('returncode') != 0:
            raise RuntimeError('baseline did not pass: ' + str(baseline))
        for identifier, module, old, new, test in MUTATIONS:
            path = folder / module
            original = path.read_text()
            if original.count(old) != 1:
                raise RuntimeError('mutation anchor not unique: ' + identifier)
            try:
                path.write_text(original.replace(old, new))
                # Avoid timestamp/size-dependent reuse of bytecode between mutants.
                shutil.rmtree(folder / '__pycache__', ignore_errors=True)
                outcome = run(folder, test)
                report['mutations'].append({'id': identifier, 'module': module, 'test': test, **outcome})
            finally:
                path.write_text(original)
    report['checkout_unchanged'] = before == fingerprint()
    report['checkout_sha256'] = before
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('scope', 'checkout_unchanged')}, ensure_ascii=False))
    for mutation in report['mutations']:
        print(mutation['id'] + ': ' + mutation['status'])
    return 0 if report['checkout_unchanged'] and all(m['status'] == 'detected' for m in report['mutations']) else 1


if __name__ == '__main__':
    sys.exit(main())
