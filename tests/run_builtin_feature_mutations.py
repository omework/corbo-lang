"""Controlled faults in temporary compiler copies; run from the repository root."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ('lowered_guarantee_omitted', 'builtin_signatures.py',
     '    if expr[0] in names:', '    if False:',
     'test_parser_lowered_method_cannot_bypass_abstract_guarantee'),
    ('builtin_signature_ignored', 'type_features.py',
     'return any(self.signatures_match(signature, expected, pending)\n                   for signature in builtin_method_signatures(actual, required.args[0]))',
     'return bool(builtin_method_signatures(actual, required.args[0]))',
     'test_builtin_signature_boundaries_against_source_level_model'),
    ('text_mode_not_normalized', 'builtin_signatures.py',
     '    mode = VALUE_SIGNATURES.get((mode, typ), mode)',
     '    mode = mode',
     'test_string_and_str_normalize_borrow_modes_and_nested_receivers'),
    ('returned_string_origin_erased', 'crust.py',
     "return 'borrowed_text', f'string_view({value})', ('uint8_t', self.growing_storage_paths(binding))",
     "return 'text', f'string_view({value})', None",
     'test_returned_string_reference_preserves_targets_and_pending_arguments'),
    ('feature_argument_tied_to_receiver', 'type_features.py',
     'concrete if index == 0 and concrete is not None else typ',
     'concrete if typ == params[0][2] and concrete is not None else typ',
     'test_type_features.TypeFeatureTests.test_method_feature_arguments_do_not_imply_equal_concrete_types'),
    ('result_feature_requirement_erased', 'type_features.py',
     'and self.satisfies(stype, rtype, pending))', 'and True)',
     'test_type_features.TypeFeatureTests.test_recursive_result_requirement_checks_leaf_even_when_unused'),
    ('recursive_requirement_guard_too_broad', 'type_features.py',
     '        if pair in pending:', '        if pending:',
     'test_type_features.TypeFeatureTests.test_recursive_result_requirement_checks_leaf_even_when_unused'),
]


def main():
    successful = True
    for name, filename, before, after, test in MUTATIONS:
        source = (ROOT / 'prototype' / filename).read_text()
        if source.count(before) != 1:
            raise SystemExit(f'{name}: mutation anchor is not unique')
        with tempfile.TemporaryDirectory(prefix='crust-builtin-feature-mut-') as folder:
            target = Path(folder)
            for path in (ROOT / 'prototype').glob('*.py'):
                shutil.copy2(path, target / path.name)
            (target / filename).write_text(source.replace(before, after))
            qualified = test if '.' in test else f'test_builtin_features.BuiltinFeatureTests.{test}'
            script = f'''import sys, unittest
sys.path[:0] = [{folder!r}, {str(ROOT / 'tests')!r}]
suite = unittest.defaultTestLoader.loadTestsFromName({qualified!r})
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=folder,
                                    capture_output=True, text=True, timeout=120)
            detected = result.returncode == 1 and (
                'FAIL:' in result.stderr or 'crust.Error:' in result.stderr)
            status = 'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE'
            print(name, status, flush=True)
            print(result.stderr[-1600:], flush=True)
            successful &= detected
    return 0 if successful else 1


if __name__ == '__main__':
    sys.exit(main())
