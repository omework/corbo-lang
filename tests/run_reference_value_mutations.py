"""Five selected reference-syntax faults, injected only in temporary copies."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from run_reference_field_mutations import ROOT, hashes

MUTATIONS=[
 ('flatten_reference_in_result_inference','results.py',
  "            if op in ('ref', 'mut') and isinstance(value, Value):\n                if value.mode in ('ref', 'mut'):",
  "            if op in ('ref', 'mut') and isinstance(value, Value):\n                if False:",
  'test_nested_reference_is_rejected_by_result_inference_alone'),
 ('implicitly_borrow_named_owner','crust.py',
  "                if arg[0] == 'name' and not existing_reference:",
  "                if False:",'test_named_owner_is_not_implicitly_borrowed_or_moved'),
 ('reject_named_reference_argument','crust.py',
  "'ref': ('ref', 'ref_expr', 'name', 'call'), 'mut': ('mut', 'mut_expr', 'name', 'call')",
  "'ref': ('ref', 'ref_expr', 'call'), 'mut': ('mut', 'mut_expr', 'call')",
  'test_create_borrow_from_owner_pass_existing_borrow_by_name'),
 ('reject_named_reference_return','crust.py',
  "                    if expr[0] == 'name' and self.lookup(expr[1]).kind in ('ref', 'mut'):",
  "                    if False:",'test_return_and_forward_reference_without_new_borrow'),
 ('forget_pool_parameter_is_borrowed','crust.py',
  "source_mut=mode == 'mut', source_borrowed=True)",
  "source_mut=mode == 'mut', source_borrowed=False)",
  'test_named_pool_parameter_is_forwarded_without_another_ampersand'),
]

def run(folder,target=None):
    command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_reference_values.py','-q']
    if target:command.extend(['-k',target])
    try:r=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired:return {'status':'inconclusive','reason':'timeout'}
    output=r.stdout+r.stderr
    broken=any(s in output for s in ('SyntaxError','ImportError','Failed to import test module'))
    status='inconclusive' if broken or 'Ran ' not in output else 'survived' if r.returncode==0 else 'detected'
    return {'status':status,'returncode':r.returncode,'output':output[-4000:]}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args();before=hashes()
    report={'scope':'five selected reference syntax faults; no global mutation rate','mutations':[]}
    with tempfile.TemporaryDirectory(prefix='crust-reference-value-mutations-') as d:
        folder=Path(d)
        for p in (ROOT / 'prototype').glob('*.py'):shutil.copy2(p,folder/p.name)
        shutil.copytree(ROOT/'tests',folder/'tests',ignore=shutil.ignore_patterns('__pycache__'))
        report['baseline']=run(folder)
        if report['baseline'].get('returncode')!=0:raise RuntimeError(str(report['baseline']))
        for name,module,old,new,test in MUTATIONS:
            p=folder/module;original=p.read_text()
            if original.count(old)!=1:raise RuntimeError('non-unique mutation anchor: '+name)
            try:
                p.write_text(original.replace(old,new));shutil.rmtree(folder/'__pycache__',ignore_errors=True)
                report['mutations'].append({'id':name,'module':module,'test':test,**run(folder,test)})
            finally:p.write_text(original)
    report['checkout_unchanged']=before==hashes();report['checkout_sha256']=before
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for m in report['mutations']:print(m['id']+': '+m['status'])
    print('checkout unchanged:',report['checkout_unchanged'])
    return 0 if report['checkout_unchanged'] and all(m['status']=='detected' for m in report['mutations']) else 1

if __name__=='__main__':sys.exit(main())
