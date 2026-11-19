"""Existing typed, computed and ABI cases affected by plain join materialization."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT / 'prototype'),str(ROOT/'tests')]
import test_async_runtime
names=(
 'test_async_local_bool_keeps_type_across_yield_and_scope_exit',
 'test_async_bool_result_preserves_type_through_await',
 'test_threaded_bool_result_preserves_type_in_ok_branch',
 'test_async_bool_control_results_preserve_branch_type',
 'test_async_loop_breaks_infer_bool_after_continue',
 'test_async_conditions_infer_bool_and_keep_operand_order',
 'test_async_spawn_array_result_uses_shaped_join_storage',
 'test_array_result_handle_requires_wait_and_internal_release_is_exactly_once',
 'test_async_await_computed_handle_preserves_result_loans',
 'test_async_computed_await_receives_borrowed_and_owned_results',
 'test_crust_spawn_and_join_expose_scalar_result_and_start_error',
 'test_generated_states_preserve_values_across_yield_and_use_typed_slots',
 'test_async_scalar_body_verifies_types_and_mutability',
 'test_pool_reuses_slots_only_after_concurrent_tasks_release_them',
 'test_task_resumes_once_and_releases_only_after_result_is_taken',
)
suite=unittest.TestSuite(test_async_runtime.AsyncRuntimeTests(name) for name in names)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
