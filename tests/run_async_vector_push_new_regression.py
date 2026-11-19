"""Neighbor contracts, ABI, UTF-8 loans, arrays and synchronous initialization."""
from pathlib import Path
import sys
import unittest
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'prototype')]
import test_async_runtime as runtime
import test_foundation_rules as foundations

# Keep the targeted ABI list in its existing runner; discover the relevant
# borrow interactions by their stable unittest names.
if __name__ == '__main__':
    names=[name for name in dir(runtime.AsyncRuntimeTests) if name.startswith('test_')
           and any(term in name for term in ('borrow','recapture','relay','abi','fixed_array_elements'))]
    suite=unittest.TestSuite(runtime.AsyncRuntimeTests(name) for name in names)
    for cls in vars(foundations).values():
        if isinstance(cls,type) and issubclass(cls,unittest.TestCase) and cls.__module__==foundations.__name__:
            suite.addTests(cls(name) for name in dir(cls) if name.startswith('test_')
                           and ('push_new' in name or 'mutable_byte_signatures' in name))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
