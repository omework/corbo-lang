"""Faults in async output placement, lifetime contracts and cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('exclude_local_graph', 'async_result_storage.py',
  "candidate.source.kind not in ('source_parameter', 'local_value')", "candidate.source.kind != 'source_parameter'", 'test_recorded_local_owned_result'),
 ('forget_descendant_storage', 'async_result_storage.py',
  'parameters.update(source.index for _, symbols in graph[1] for source in symbols)', 'pass # missing retained descendants', 'test_short_pool_rejected_before_and_after_wait'),
 ('omit_direct_graph_fields', 'crust.py',
  'graph = pool_result_graph(node, self.enums)', 'graph = None', 'test_recorded_local_owned_result'),
 ('omit_nested_parameter_fields', 'async_result_storage.py',
  'if enums is not None:', 'if False:', 'test_each_descendant_pool_must_survive_result'),
 ('omit_factory_output', 'results.py',
  "if symbol.kind == 'task_output':\n                                sources.add(symbol)", "if symbol.kind == 'task_output':\n                                pass", 'test_factory_and_result_source'),
 ('omit_graph_placement', 'async_local_placement.py',
  'plan.parameters == frozenset() or pool_result_graph(node) is not None', 'plan.parameters == frozenset()', 'test_async_caller_parent_and_relay'),
 ('close_external_root_storage', 'async_lowering.py',
  "local_pools[destination] = '(*frame->result_storage)'", "local_pools[destination] = '(*frame->result_storage)'\n        scopes[0][0][destination] = None", 'test_identity_and_suspended_cleanup'),
 ('omit_owned_graph_completion', 'async_structure_effects.py',
  "owned_graph = mode in ('owned', 'join_owned', 'join_nested')", "owned_graph = False and mode in ('owned', 'join_owned', 'join_nested')", 'test_nested_owned_descendant_sources'),
)


def main():
 suite='test_async_local_owned_result_graphs.AsyncLocalOwnedResultGraphTests'
 baseline=run(ROOT,suite)
 print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,filename,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-local-owned-result-graph-') as directory:
   target=Path(directory)
   for path in (ROOT / 'prototype').glob('*.py'):shutil.copy2(path,target/path.name)
   path=target/filename;source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  print(name,'DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE',flush=True)
  print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)

if __name__=='__main__':sys.exit(main())
