"""Contract and scope-exit interactions for synchronous boolean state calls."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from test_foundation_rules import FoundationTests

loader = unittest.defaultTestLoader
suite = unittest.TestSuite()
for module in ('test_arguments', 'test_direct_borrow_returns', 'test_mutable_borrow_returns',
               'test_modular_calls', 'test_function_bodies'):
    suite.addTests(loader.loadTestsFromName(module))
for name in loader.getTestCaseNames(FoundationTests):
    if any(word in name for word in ('block', 'short_circuit', 'condition', 'boolean',
                                     'scalar', 'primitive', 'return')):
        suite.addTest(FoundationTests(name))
print(f'{suite.countTestCases()} selected methods', flush=True)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
