from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'prototype'), str(root/'tests')]
from test_public_structure_handles import PublicStructureHandleTests as Tests

counts = {'native': 0, 'invalid_programs': 0, 'rejection_checks': 0}
original_run, original_refused = Tests.run_c_oracle, Tests.refused


def run(self, *args, **kwargs):
    result = original_run(self, *args, **kwargs)
    counts['native'] += 1
    return result


def refused(self, *args, **kwargs):
    counts['invalid_programs'] += 1
    counts['rejection_checks'] += 2
    return original_refused(self, *args, **kwargs)


Tests.run_c_oracle, Tests.refused = run, refused
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
print(counts, flush=True)
sys.exit(not result.wasSuccessful())
