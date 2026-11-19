#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Compile/run complete README examples with corboc and verify source synchronization."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[1]
EXAMPLES=ROOT/'examples/features'


def main():
    """Retain generated C, diagnostics, expected results and a completed JSON report."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corboc',type=Path,required=True)
    parser.add_argument('--keep',type=Path,default=ROOT/'build/documentation')
    parser.add_argument('--cc',default='cc')
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--only',help='run one named example')
    parser.add_argument('--check-limits',action='store_true',help='replay historical observations, expecting acceptance for resolved forms')
    parser.add_argument('--sources-only',action='store_true',help='development: omit README/source comparison')
    args=parser.parse_args();args.keep=args.keep.resolve();args.keep.mkdir(parents=True,exist_ok=True)
    cases=json.loads((EXAMPLES/'manifest.json').read_text())
    if not args.sources_only:
        readme=(ROOT/'README.md').read_text()
        blocks=dict(re.findall(r'<!-- example: ([a-z_]+) -->\s*```rust\n(.*?)```',readme,re.S))
        for case in cases:
            expected=(EXAMPLES/case['name']/'src/main.crb').read_text()
            if blocks.get(case['name'])!=expected:raise ValueError('README/source mismatch: '+case['name'])
        if len(blocks)!=len(cases):raise ValueError('README contains extra or missing executable example markers')
    if not args.sources_only:
        auxiliary=re.findall(r'<!-- example-file: ([a-zA-Z0-9_./-]+) -->\s*```(?:rust|toml)\n(.*?)```',readme,re.S)
        for relative,body in auxiliary:
            path=(EXAMPLES/relative).resolve()
            if not path.is_relative_to(EXAMPLES.resolve()) or path.read_text()!=body:raise ValueError('README auxiliary-file mismatch: '+relative)
    observations=[]
    if args.check_limits:
        limit_root=ROOT/'validation/fixtures/documentation_limits'
        resolved={row['name'] for row in json.loads((limit_root/'resolved.json').read_text())}
        for case in json.loads((limit_root/'observed.json').read_text()):
            result=subprocess.run([args.corboc.resolve(),'--emit-package-c',limit_root/case['name'],'--stdlib-dir',ROOT/'stdlib/src'],capture_output=True,text=True,timeout=120)
            fixed=case['name'] in resolved
            matched=(result.returncode==0 and not result.stderr) if fixed else (result.returncode,result.stdout,result.stderr)==(case['status'],case['stdout'],case['stderr'])
            observations.append({'name':case['name'],'matches_record':matched,'status':result.returncode,'stdout':result.stdout if result.returncode else '', 'stderr':result.stderr,'resolved':fixed})
        (args.keep/'limits-report.json').write_text(json.dumps(observations,indent=2)+'\n')
        if not all(case['matches_record']for case in observations):raise ValueError('Compiler coverage replay failed; review DOCUMENTATION_LIMITS.md')
        print('Historical coverage observations replayed: '+str(len(observations)))
    if args.only:
        cases=[case for case in cases if case['name']==args.only]
        if not cases:parser.error('unknown example: '+args.only)
    def run(case):
        name=case['name'];keep=args.keep/name;keep.mkdir(exist_ok=True)
        c=keep/'program.c';binary=keep/'program';package=EXAMPLES/name
        result=subprocess.run([args.corboc.resolve(),'--emit-package-c',package,'--stdlib-dir',ROOT/'stdlib/src'],capture_output=True,timeout=120)
        (keep/'compile.stderr').write_bytes(result.stderr)
        if result.returncode:
            (keep/'compile.stdout').write_bytes(result.stdout)
            return {'name':name,'passed':False,'stage':'corboc','status':result.returncode,'diagnostic':(result.stdout+result.stderr).decode(errors='replace')[:1000]}
        c.write_bytes(result.stdout)
        result=subprocess.run([*shlex.split(args.cc),'-std=c11','-pthread','-O1','-fsanitize=undefined','-fno-sanitize-recover=all',c,'-lm','-o',binary],capture_output=True,timeout=120)
        (keep/'cc.stderr').write_bytes(result.stderr)
        if result.returncode:return {'name':name,'passed':False,'stage':'C','diagnostic':result.stderr.decode(errors='replace')[:1000]}
        result=subprocess.run([binary],cwd=keep,capture_output=True,text=True,timeout=30)
        (keep/'stdout').write_text(result.stdout);(keep/'stderr').write_text(result.stderr)
        return {'name':name,'passed':(result.returncode,result.stdout,result.stderr)==(0,case['stdout'],''),'stage':'execution','status':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:rows=list(pool.map(run,cases))
    report={'compiler':str(args.corboc.resolve()),'configuration':'host, O1, fatal UBSan','readme_synchronized':not args.sources_only,'examples':rows,'observations_replayed':len(observations),'all_passed':all(row['passed']for row in rows)}
    (args.keep/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    for row in rows:print(('PASS 'if row['passed']else'FAIL ')+row['name']+(''if row['passed']else' '+json.dumps(row)))
    if not report['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
