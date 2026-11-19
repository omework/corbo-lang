"""Replay relevant existing scenarios with ordinary and explicitly blocking launches."""
import ast
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT / 'prototype'),str(ROOT/'tests')]
import test_async_runtime

source=(ROOT/'tests/test_async_runtime.py').read_text()
selected=[]
for node in ast.walk(ast.parse(source)):
    if isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):
        segment=ast.get_source_segment(source,node)
        if ('runtime::Error' in segment or 'scheduler' in node.name
                or node.name in ('test_mutable_capture_reserves_before_start_and_until_join',
                    'test_async_iteration_waits_for_worker_before_reusing_local',
                    'test_async_if_transfers_task_or_handle_with_all_possible_captures',
                    'test_async_utf8_handle_transfer_keeps_join_obligation')):
            selected.append(node.name)
blocking='--blocking' in sys.argv
if blocking:
    compile_source=test_async_runtime.compile_source
    verify_program=test_async_runtime.verify_program
    test_async_runtime.compile_source=lambda source,**kwargs: compile_source(
        source.replace('runtime::spawn(', 'runtime::spawn_blocking('),**kwargs)
    test_async_runtime.verify_program=lambda source,**kwargs: verify_program(
        source.replace('runtime::spawn(', 'runtime::spawn_blocking('),**kwargs)
print('blocking' if blocking else 'ordinary',len(selected),'selected methods',flush=True)
suite=unittest.TestSuite(test_async_runtime.AsyncRuntimeTests(name) for name in selected)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
