"""Targeted regression; --inject exercises the feature pass on existing cases."""
import ast
import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'prototype'), str(ROOT / 'tests')]


def main():
    import test_foundation_rules as foundation
    suite = unittest.TestSuite()
    if '--inject' in sys.argv:
        prefix = ('type feature UnusedFeatureProbe{fn feature_probe(&self);}'
                  'fn unused_feature_relay(x:&UnusedFeatureProbe){x.feature_probe();}\n')
        compile_original, verify_original = foundation.compile_source, foundation.verify_program
        foundation.compile_source = lambda source, *a, **kw: compile_original(prefix + source, *a, **kw)
        foundation.verify_program = lambda source, *a, **kw: verify_original(prefix + source, *a, **kw)
    else:
        for module in ('test_modular_calls', 'test_function_bodies', 'test_pool_requirements',
                       'test_direct_borrow_returns', 'test_mutable_borrow_returns', 'test_growth_annotations'):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(module)))
    for cls in ast.parse(Path(foundation.__file__).read_text()).body:
        if isinstance(cls, ast.ClassDef):
            for member in cls.body:
                if (isinstance(member, ast.FunctionDef) and member.name.startswith('test_')
                        and ('method' in member.name or member.name.startswith('test_local_structure'))):
                    suite.addTest(foundation.FoundationTests(member.name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
