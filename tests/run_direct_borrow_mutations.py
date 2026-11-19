"""Selected direct-reference faults in temporary copies; no global mutation rate."""
import run_borrowed_return_mutations as runner

runner.MUTATIONS=[
 ('omit_direct_target_contract','results.py',
  "borrowed_targets(Value('ref', 'Int', frozenset(self.returned))) if self.declared[0] in ('ref', 'mut') else frozenset()",
  'frozenset()', 'test_contract_records_target_without_owned_candidate'),
 ('accept_local_direct_target','results.py',
  "if target.kind == 'local' or self.params[target.parameter][1] not in ('ref', 'mut'):",
  'if False:', 'test_local_target_rejected_by_result_inference_alone'),
 ('forget_alias_alternatives','crust.py',
  '            self.referents = descriptor.reference_targets',
  '            self.referents = ()','test_conditional_result_protects_every_possible_target'),
 ('forget_mutable_parent','crust.py',
  '            self.borrow_parents = descriptor.borrow_parents',
  '            self.borrow_parents = ()','test_conditional_mutable_parents_resume_after_last_use'),
 ('reject_ancestor_direct_target','crust.py',
  'not target.definite or target.scope not in scopes:',
  'not target.definite or target.scope in scopes:','test_parent_and_ancestor_targets_survive_nested_return_boundaries'),
]
# Reuse transport, timeout, import-failure classification, hashes and temporary-copy cleanup.
original_run=runner.run
def run(folder,target=None):
    import subprocess,sys
    command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_direct_borrow_returns.py','-q']
    if target:command.extend(['-k',target])
    try:r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired:return {'status':'inconclusive','reason':'timeout'}
    output=r.stdout+r.stderr
    broken=any(s in output for s in ('SyntaxError','ImportError','Failed to import test module'))
    status='inconclusive' if broken or 'Ran ' not in output else 'survived' if r.returncode==0 else 'detected'
    return {'status':status,'returncode':r.returncode,'output':output[-4000:]}
runner.run=run
if __name__=='__main__':
    import sys
    sys.exit(runner.main())
