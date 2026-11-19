"""Selected field-dependency faults, injected only in temporary copies."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
 ('omit_constructor_dependencies', 'crust.py',
  'dependencies=tuple(dependencies), variants=frozenset({arm})',
  'dependencies=(), variants=frozenset({arm})', 'test_read_field_through_function_and_match'),
 ('omit_field_contract_source', 'constraints.py',
  '                            fields.append((key, frozenset({target})))', '                            pass',
  'test_opaque_contract_protects_field_source_without_body_access'),
 ('omit_pending_field_borrow', 'crust.py',
  "                    frame.append(Binding(name, field_mode, c, target, read_parent=read_parent,\n                                         referents=targets, borrow_parents=reference_parents))", '                    pass',
  'test_pending_reference_field_survives_later_initializer_effects'),
 ('wrong_pointer_field_offsets', 'crust.py',
  "return ' + '.join('sizeof(Cell *)' if typ in ('&Int', '&mut Int') else 'sizeof(int)'",
  "return ' + '.join('sizeof(int)'",
  'test_mixed_layout_and_addresses_are_preserved'),
]


def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted([*(ROOT / 'prototype').glob('*.py'),*(ROOT/'tests').glob('*.py')])}


def run(folder, target=None):
    cmd=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_reference_fields.py','-q']
    if target:
        cmd.extend(['-k',target])
    try:
        r=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,timeout=60)
    except subprocess.TimeoutExpired:
        return {'status':'inconclusive','reason':'timeout'}
    output=r.stdout+r.stderr
    broken=any(s in output for s in ('SyntaxError','ImportError','Failed to import test module'))
    status='inconclusive' if broken or 'Ran ' not in output else 'survived' if r.returncode==0 else 'detected'
    return {'status':status,'returncode':r.returncode,'output':output[-4000:]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    before=hashes()
    report={'scope':'four selected faults, no global detection rate','mutations':[]}
    with tempfile.TemporaryDirectory(prefix='crust-ref-mutations-') as d:
        folder=Path(d)
        for p in (ROOT / 'prototype').glob('*.py'):
            shutil.copy2(p,folder/p.name)
        shutil.copytree(ROOT/'tests',folder/'tests',ignore=shutil.ignore_patterns('__pycache__'))
        report['baseline']=run(folder)
        if report['baseline'].get('returncode')!=0:
            raise RuntimeError(str(report['baseline']))
        for name,module,old,new,test in MUTATIONS:
            p=folder/module
            original=p.read_text()
            if original.count(old)!=1:
                raise RuntimeError('non-unique mutation anchor: '+name)
            try:
                p.write_text(original.replace(old,new))
                shutil.rmtree(folder/'__pycache__',ignore_errors=True)
                outcome=run(folder,test)
                report['mutations'].append({'id':name,'module':module,'test':test,**outcome})
            finally:
                p.write_text(original)
    report['checkout_unchanged']=before==hashes()
    report['checkout_sha256']=before
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for m in report['mutations']:
        print(m['id']+': '+m['status'])
    print('checkout unchanged:',report['checkout_unchanged'])
    return 0 if report['checkout_unchanged'] and all(m['status']=='detected' for m in report['mutations']) else 1


if __name__=='__main__':
    sys.exit(main())
