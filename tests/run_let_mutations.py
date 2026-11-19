"""Selected mutability, identity and contract faults, injected only in copies."""
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from run_reference_field_mutations import ROOT,hashes
MUTATIONS=[
 ('ignore_immutable_binding','crust.py',
  "if write and binding.kind in ('owned', 'scalar') and not binding.mutable:",
  "if False:",'test_immutable_owner_cannot_be_mutated_or_borrowed_mutably'),
 ('require_mut_binding_for_mutable_reference','crust.py',
  "if write and binding.kind in ('owned', 'scalar') and not binding.mutable:",
  "if write and binding.kind in ('owned', 'scalar', 'mut') and not binding.mutable:",
  'test_immutable_binding_to_mutable_reference_can_mutate_target'),
 ('allocate_instead_of_content_write','crust.py',
  "self.lines.append(f'{target.c}->value = {c};')",
  "self.lines.append(f'{target.c} = cell_new({target.c}->source, {c}, \"mutation\");')",
  'test_assignment_and_method_mutate_the_same_allocation'),
 ('forget_owned_identity_after_content_write','results.py',
  "previous.mode == 'owned' and isinstance(value, Value) and value.mode == 'scalar'",
  "False",'test_content_write_preserves_return_contract_identity'),
 ('forget_write_target_reset_history','constraints.py',
  "                            self.touch(previous, following['next'], line)",
  "                            pass",'test_wrapper_contract_keeps_write_target_source_history'),
]

def run(folder,target=None):
    cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_let_mutability.py','-q']
    if target:cmd.extend(['-k',target])
    try:r=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,timeout=90)
    except subprocess.TimeoutExpired:return {'status':'inconclusive','reason':'timeout'}
    output=r.stdout+r.stderr
    broken=any(s in output for s in ('SyntaxError','ImportError','Failed to import test module'))
    return {'status':'inconclusive' if broken or 'Ran ' not in output else 'survived' if r.returncode==0 else 'detected',
            'returncode':r.returncode,'output':output[-5000:]}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args();before=hashes();report={'scope':'five selected faults, no global rate','mutations':[]}
    with tempfile.TemporaryDirectory(prefix='crust-let-mutations-') as d:
        folder=Path(d)
        for p in (ROOT / 'prototype').glob('*.py'):shutil.copy2(p,folder/p.name)
        shutil.copytree(ROOT/'tests',folder/'tests',ignore=shutil.ignore_patterns('__pycache__'))
        report['baseline']=run(folder)
        if report['baseline']['returncode']!=0:raise RuntimeError(str(report['baseline']))
        for name,module,old,new,target in MUTATIONS:
            p=folder/module;original=p.read_text()
            if original.count(old)!=1:raise RuntimeError('non-unique anchor: '+name)
            try:
                p.write_text(original.replace(old,new));shutil.rmtree(folder/'__pycache__',ignore_errors=True)
                report['mutations'].append({'id':name,'module':module,'test':target,**run(folder,target)})
            finally:p.write_text(original)
    report['checkout_unchanged']=before==hashes();report['checkout_sha256']=before
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for m in report['mutations']:print(m['id']+': '+m['status'])
    print('checkout unchanged:',report['checkout_unchanged'])
    return 0 if report['checkout_unchanged'] and all(m['status']=='detected' for m in report['mutations']) else 1
if __name__=='__main__':sys.exit(main())
