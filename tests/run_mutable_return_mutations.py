"""Selected exclusive-return faults; temporary copies only, no global rate."""
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from run_reference_field_mutations import ROOT,hashes
MUTATIONS=[
 ('downgrade_opaque_mutable_result','crust.py',
  '            return result.mode, c, descriptor',
  "            return 'ref', c, descriptor",'test_original_accesses_are_blocked_until_last_use'),
 ('downgrade_secondary_target_loan','crust.py',
  '                result.append(binding)',
  "                result.append(binding if binding.alloc is allocation else Binding('mutant', 'ref', '', allocation))",
  'test_union_of_mutable_parents_resumes_after_last_use'),
 ('forget_mutable_result_parent','crust.py',
  '            self.borrow_parents = descriptor.borrow_parents',
  "            self.borrow_parents = () if self.kind == 'mut' else descriptor.borrow_parents",
  'test_successive_calls_preserve_exclusive_target_and_parents'),
 ('allow_shared_parameter_upgrade_in_contract','crust.py',
  "            if summary.mode == 'mut' and binding.kind != 'mut':",
  '            if False:','test_forged_mutable_contract_cannot_upgrade_shared_input'),
 ('end_owned_binding_at_content_write','crust.py',
  "                if (node.op == 'assign' and kind == 'owned'",
  '                if (False',
  'test_content_write_is_an_explicit_use_without_ending_owned_binding'),
]
def run(folder,target=None):
    cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_mutable_borrow_returns.py','-q']
    if target:cmd.extend(['-k',target])
    try:r=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,timeout=90)
    except subprocess.TimeoutExpired:return {'status':'inconclusive','reason':'timeout'}
    output=r.stdout+r.stderr
    broken=any(s in output for s in ('SyntaxError','ImportError','Failed to import test module'))
    return {'status':'inconclusive' if broken or 'Ran ' not in output else 'survived' if r.returncode==0 else 'detected',
            'returncode':r.returncode,'output':output[-5000:]}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args();before=hashes();report={'scope':'five selected mutable return faults; no global rate','mutations':[]}
    with tempfile.TemporaryDirectory(prefix='crust-mut-return-mutations-') as d:
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
