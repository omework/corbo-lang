"""Selected faults in borrowed result inference and boundary checks, in copies only."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from run_reference_field_mutations import ROOT, hashes

MUTATIONS=[
 ('omit_result_field_contract','results.py',
  '            self.returned_fields[name] = self.returned_fields.get(name, frozenset()) | targets',
  '            pass','test_make_view_contract_records_input_identity'),
 ('omit_opaque_result_dependencies','crust.py',
  '        target.dependencies, target.variants = dependencies, variants',
  '        target.dependencies, target.variants = (), variants','test_basic_return_uses_parent_target_and_keeps_address'),
 ('accept_local_field_target_in_inference','results.py',
  "if (target.kind == 'local' or", "if (False or",'test_result_inference_rejects_local_target_without_memory_backend'),
 ('reject_ancestor_targets','crust.py',
  'not target.definite or target.scope not in scopes:',
  'not target.definite or target.scope in scopes:','test_successive_nested_blocks_verify_each_parent_boundary'),
 ('lose_mutable_parent_of_result','crust.py',
  '                parents.update((id(p), p) for p in (*candidates, *binding.borrow_parents))',
  '                pass','test_returned_shared_reborrow_suspends_then_restores_mutable_parent'),
]


def run(folder,target=None):
    command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_borrowed_returns.py','-q']
    if target:command.extend(['-k',target])
    try:r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired:return {'status':'inconclusive','reason':'timeout'}
    output=r.stdout+r.stderr
    broken=any(s in output for s in ('SyntaxError','ImportError','Failed to import test module'))
    status='inconclusive' if broken or 'Ran ' not in output else 'survived' if r.returncode==0 else 'detected'
    return {'status':status,'returncode':r.returncode,'output':output[-4000:]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    before=hashes();report={'scope':'five selected borrowed return faults; no global rate','mutations':[]}
    with tempfile.TemporaryDirectory(prefix='crust-return-mutations-') as d:
        folder=Path(d)
        for p in (ROOT / 'prototype').glob('*.py'):shutil.copy2(p,folder/p.name)
        shutil.copytree(ROOT/'tests',folder/'tests',ignore=shutil.ignore_patterns('__pycache__'))
        report['baseline']=run(folder)
        if report['baseline'].get('returncode')!=0:raise RuntimeError(str(report['baseline']))
        for name,module,old,new,test in MUTATIONS:
            path=folder/module;original=path.read_text()
            if original.count(old)!=1:raise RuntimeError('non-unique mutation anchor: '+name)
            try:
                path.write_text(original.replace(old,new));shutil.rmtree(folder/'__pycache__',ignore_errors=True)
                report['mutations'].append({'id':name,'module':module,'test':test,**run(folder,test)})
            finally:path.write_text(original)
    report['checkout_unchanged']=before==hashes();report['checkout_sha256']=before
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for m in report['mutations']:print(m['id']+': '+m['status'])
    print('checkout unchanged:',report['checkout_unchanged'])
    return 0 if report['checkout_unchanged'] and all(m['status']=='detected' for m in report['mutations']) else 1


if __name__=='__main__':sys.exit(main())
