"""Fixed mixed-field layouts and capacity failures under optimized C/UBSan."""
from functools import partial, update_wrapper
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototype'))
from crust import compile_source

# These regressions exercise the historical reset profile.
compile_source = update_wrapper(partial(compile_source, allow_legacy_reset=True), compile_source)
from validate_pool_contract_c import toolchains

PREFIX='''
enum View { Item { prefix: Int, left: &Int, middle: Int, right: &Int, tail: Int }, Empty {} }
fn use_view(v: &View) {
    match &v {
        View.Item {prefix:a,left:x,middle:b,right:y,tail:c} => {print(a);print(x);print(b);print(y);print(c);address(x);},
        View.Empty {} => {}
    }
}
'''
PROGRAMS={
 'mixed':PREFIX+'''fn main(){
    let mut p=pool<Int>(2);let mut q=pool<View>(1);
    let mut x=new(p)Int(10);let mut y=new(p)Int(20);address(x);
    let mut v=new(q)View.Item{prefix:1,left:&x,middle:2,right:&y,tail:3};
    use_view(&v);print(v);drop(->x);drop(->y);
 }''',
 'empty':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut q=pool<View>(1);
    let mut x=new(p)Int(10);let mut v=new(q)View.Empty{};
    p.reset();use_view(&v);print(v);
 }''',
 'exhaustion':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut x=new(p)Int(10);
    let mut a=new(q)View.Item{prefix:1,left:&x,middle:2,right:&x,tail:3};
    let mut b=new(q)View.Item{prefix:4,left:&x,middle:5,right:&x,tail:6};
    print(a);print(b);
 }'''
}


def validate(result,case):
    assert 'runtime error:' not in result.stderr,result.stderr
    if case=='exhaustion':
        assert result.returncode!=0 and 'pool capacity exceeded' in result.stderr,result.stderr
        assert 'destroy ' not in result.stderr and result.stdout=='',result.stderr
        return
    assert result.returncode==0,result.stderr
    lines=result.stdout.splitlines()
    if case=='mixed':
        assert lines[0]==lines[6],lines
        assert lines[1:6]==['1','10','2','20','3'],lines
        assert lines[7:]==['View.Item(1, 10, 2, 20, 3)'],lines
        drops=['destroy x=10','destroy y=20','destroy v=View.Item']
    else:
        assert lines==['View.Empty()'],lines
        drops=['destroy x=10','destroy v=View.Empty']
    assert [s for s in result.stderr.splitlines() if s.startswith('destroy ')]==drops,result.stderr


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    compilers=toolchains()
    if not compilers:
        raise RuntimeError('no C compiler')
    configurations=[('O0',['-O0']),('O2',['-O2']),('Os',['-Os']),
                    ('O2-UBSan',['-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer'])]
    report={'toolchains':compilers,'runs':[],'limitations':['three fixed programs, not all layouts','ASan not available on host']}
    with tempfile.TemporaryDirectory(prefix='crust-ref-c-') as d:
        folder=Path(d)
        for case,source in PROGRAMS.items():
            path,binary=folder/'program.c',folder/'program'
            path.write_text(compile_source(source))
            for cc in compilers:
                for label,options in configurations:
                    cmd=[cc['path'],'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-Wno-unused-function',
                         *options,str(path),'-o',str(binary)]
                    build=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
                    if build.returncode:
                        raise RuntimeError(build.stderr)
                    result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=10,
                                          env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1'))
                    validate(result,case)
                    report['runs'].append({'case':case,'compiler':cc['family'],'settings':label,'returncode':result.returncode,
                                           'stdout':result.stdout,'stderr':result.stderr})
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(len(report['runs']),'C executions satisfied specified values, identities, destruction and exhaustion checks')


if __name__=='__main__':
    main()
