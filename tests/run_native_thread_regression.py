"""Reproducible RT8 boundary regression selection (CRUST_TEST_OPT controls C)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
import test_async_runtime

loader = unittest.defaultTestLoader
suite = unittest.TestSuite()
for name in ('test_native_thread_runtime', 'test_native_thread_parser', 'test_native_blocks', 'test_native_sync_calls', 'test_sync_borrow_calls', 'test_sync_byte_borrows', 'test_sync_owned_calls', 'test_sync_bool_calls', 'test_async_pool_injection',
             'test_async_collection_new', 'test_async_local_pools', 'test_async_pool_aliases', 'test_async_regions', 'test_async_struct_captures', 'test_async_struct_reference_fields', 'test_spawn_blocking', 'test_handle_obligations',
             'test_async_typed_divergence', 'test_async_field_reborrows', 'test_async_field_reference_returns',
             'test_async_helper_result_contracts', 'test_async_detached_field_returns', 'test_stored_field_reborrows',
             'test_task_wakes', 'test_ready_queue', 'test_await_notifications'):
    suite.addTests(loader.loadTestsFromName(name))
for name in loader.getTestCaseNames(test_async_runtime.AsyncRuntimeTests):
    if any(word in name for word in ('thread', 'scheduler', 'worker', 'spawn', 'cleanup', 'pool_reuse')):
        suite.addTest(test_async_runtime.AsyncRuntimeTests(name))
print(f'{suite.countTestCases()} selected methods', flush=True)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
