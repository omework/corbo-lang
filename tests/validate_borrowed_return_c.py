"""C observations for borrowed object returns, successive calls and mutable reborrows."""
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
enum View { Item {data: &Int}, Empty {} }
fn make_view(q:&mut Pool<View>,data:&Int)-><-View{
    let mut view=new(q)View.Item{data:data};return<-view;
}
fn middle(q:&mut Pool<View>,data:&Int)-><-View{
    let mut view=make_view(q,data);return<-view;
}
fn outer(q:&mut Pool<View>,data:&Int)-><-View{
    let mut view=middle(q,data);return<-view;
}
fn forward(mut view:->View)-><-View{return<-view;}
'''
PROGRAMS={
 'readonly':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut data=new(p)Int(42);address(data);
    let mut first=outer(&mut q,&data);address(first);
    let mut view=forward(->first);address(view);
    match &view {View.Item{data:r}=>{address(r);print(r);},View.Empty{}=>{}}
    drop(->data);q.reset();
 }''',
 'mutable_parent':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut data=new(p)Int(42);
    let mut loan=&mut data;let mut view=outer(&mut q,loan);print(view);
    loan.set(7);print(loan);
 }''',
 'exhaustion':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut q=pool<View>(1);let mut data=new(p)Int(42);
    let mut first=outer(&mut q,&data);print(first);
    let mut second=outer(&mut q,&data);print(second);
 }'''
}


def validate(result,case):
    assert 'runtime error:' not in result.stderr,result.stderr
    if case=='exhaustion':
        assert result.returncode!=0 and 'pool capacity exceeded' in result.stderr,result.stderr
        assert result.stdout=='View.Item(42)\n' and 'destroy ' not in result.stderr,(result.stdout,result.stderr)
        return
    assert result.returncode==0,result.stderr
    lines=result.stdout.splitlines()
    if case=='readonly':
        assert len(lines)==5 and lines[0]==lines[3] and lines[1]==lines[2] and lines[4]=='42',lines
        expected=['destroy data=42','destroy view=View.Item']
    else:
        assert lines==['View.Item(42)','7'],lines
        expected=['destroy view=View.Item','destroy data=7']
    assert [s for s in result.stderr.splitlines() if s.startswith('destroy ')]==expected,result.stderr


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    compilers=toolchains()
    if not compilers:
        raise RuntimeError('no C compiler')
    configs=[('O0',['-O0']),('O2',['-O2']),('Os',['-Os']),
             ('O2-UBSan',['-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer'])]
    report={'toolchains':compilers,'runs':[],'limits':['three fixed programs, no proof','ASan not available on host']}
    with tempfile.TemporaryDirectory(prefix='crust-return-c-') as d:
        folder=Path(d)
        for case,source in PROGRAMS.items():
            c,binary=folder/'program.c',folder/'program'
            c.write_text(compile_source(source))
            for compiler in compilers:
                for label,options in configs:
                    command=[compiler['path'],'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-Wno-unused-function',
                             *options,str(c),'-o',str(binary)]
                    build=subprocess.run(command,capture_output=True,text=True,timeout=30)
                    if build.returncode:
                        raise RuntimeError(build.stderr)
                    result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=10,
                                          env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1'))
                    validate(result,case)
                    report['runs'].append({'case':case,'compiler':compiler['family'],'configuration':label,
                                           'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(len(report['runs']),'C executions satisfied the specified observations')


if __name__=='__main__':
    main()
