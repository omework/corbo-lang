"""Temporary faults in pool layout, lifetime retention and construction cleanup."""
from pathlib import Path
import shutil
import sys
import tempfile
from run_suspended_cleanup_mutations import run
ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=(
 ('corrupt_field_offsets', "return ' + '.join('sizeof(int)' if kind == 'Int' else 'sizeof(Cell *)'\n                          for _, kind in layout[:index]) or '0'", "return '0'", 'test_defaults_named_order_and_multiple_slots'),
 ('forget_owned_field_destructor', '{2 if field_type.startswith("A<") else 1 if field_type.startswith("&") else 0}', '{0}', 'test_ownership_of_fields_and_cross_pool_lifetimes'),
 ('forget_descendant_pool', 'storage.update(storage_of(value))', 'pass # lost descendant source', 'test_ownership_of_fields_and_cross_pool_lifetimes'),
 ('lose_prepared_owner', '                    owners.append(snapshot)', '                    pass # lost prepared owner', 'test_pending_owner_cleanup_during_later_field'),
 ('wrong_default', "                values[field] = '0'", "                values[field] = '1'", 'test_defaults_named_order_and_multiple_slots'),
 ('lose_direct_graph', 'graph = pool_result_graph(node, self.enums)', 'graph = None', 'test_nested_owned_graph_and_injected_source_return'),
 ('lose_factory_graph', 'graph = pool_result_graph(declaration, self.analyzer.enums)', 'graph = None', 'test_fresh_graph_factory_and_short_descendant_pool'),
 ('late_scalar_read', '                values[field] = snapshot', "                values[field] = value if field_type == 'Int' else snapshot", 'test_scalar_snapshot_and_borrowed_arguments'),
)
def main():
 suite='test_async_struct_pools.AsyncStructPoolTests'
 baseline=run(ROOT,suite);print('BASELINE',baseline.returncode,baseline.stdout+baseline.stderr,flush=True)
 if baseline.returncode:return 1
 ok=True
 for name,before,after,method in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='crust-struct-pool-mutant-') as directory:
   target=Path(directory)
   for file in (ROOT / 'prototype').glob('*.py'):shutil.copy2(file,target/file.name)
   filename = 'results.py' if name == 'lose_factory_graph' else 'crust.py' if name == 'lose_direct_graph' else 'async_lowering.py'
   path=target/filename;source=path.read_text();assert source.count(before)==1,(name,source.count(before))
   path.write_text(source.replace(before,after));result=run(target,suite+'.'+method)
  detected=result.returncode==1 and 'AssertionError' in result.stderr
  status='DETECTED' if detected else 'SURVIVED' if not result.returncode else 'INCONCLUSIVE'
  print(name,status,flush=True);print(result.stdout+result.stderr,flush=True);ok &= detected
 return int(not ok)
if __name__=='__main__':sys.exit(main())
