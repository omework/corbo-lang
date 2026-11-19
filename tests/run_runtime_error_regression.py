"""Replay existing value/error payload paths changed by the Err binder split."""
import ast
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT / 'prototype'),str(ROOT/'tests')]
suite=unittest.TestSuite()
for module in ('test_foundation_rules','test_owned_results','test_owner_usage'):
    source=(ROOT/'tests'/f'{module}.py').read_text()
    for cls in ast.parse(source).body:
        if not isinstance(cls,ast.ClassDef):continue
        for method in cls.body:
            if (isinstance(method,ast.FunctionDef) and method.name.startswith('test_')
                    and re.search(r'Err\([a-z][a-zA-Z_]*\)',ast.get_source_segment(source,method))):
                name=f'{module}.{cls.name}.{method.name}'
                print(name,flush=True)
                suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
