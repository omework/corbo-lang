#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Compare real C and Corbo runtime implementations using the same ABI fixtures."""
import argparse,json,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime/corbo'))
from build import build,closing_brace
from exports import EXPORTS
import re
from replace import replace,SECTIONS
FIX=ROOT/'validation/fixtures/corbo_runtime'

def reference():
    order=['base_runtime','task_runtime','task_value_runtime','native_runtime','pool_runtime','reclaim_runtime','map_runtime','c_runtime_api']
    text='#define CORBO_RUNTIME_TASKS 1\n'+(ROOT/'runtime/corbo_runtime.h').read_text()
    for group in order:
        part=''.join((ROOT/'runtime'/name).read_text()for name in SECTIONS[group])
        part=part.replace('#if CORBO_THREADED\n','').replace('#endif /* CORBO_THREADED */\n','')
        text+=part
    return text

def reference_inventory():
    names={name for _,name,_,_ in EXPORTS};functions=[]
    for path in sorted((ROOT/'runtime').glob('**/*.c.inc')):
        if 'corbo' in path.parts:continue
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',path.read_text(),flags=re.S);at=0;mark=0
        while True:
            opening=text.find('{',at)
            if opening<0:break
            header=re.sub(r'__attribute__\s*\(\([^)]*\)\)','',text[mark:opening].rsplit(';',1)[-1])
            match=re.search(r'\b(\w+)\s*\(',header)
            if match:functions.append(match[1])
            at=closing_brace(text,opening);mark=at
    missing=set(functions)-names
    assert not missing,missing
    return len(functions)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compiler',type=Path,required=True);p.add_argument('--keep',type=Path,required=True);p.add_argument('--cc',default='cc');p.add_argument('--runner',default='');p.add_argument('--reuse-compiled',type=Path);a=p.parse_args();out=a.keep.resolve();out.mkdir(parents=True,exist_ok=True)
    compiled=a.reuse_compiled.resolve() if a.reuse_compiled else out/'compiled'
    if not a.reuse_compiled:build(a.compiler,compiled)
    common=reference();rows=[];inventory=reference_inventory()
    for name,expected in [('memory','memory parity passed\n'),('default_capacity','default capacity parity passed\n'),('tasks','task parity passed\n'),('failures','failure parity passed\n'),('readiness','readiness parity passed\n'),('completion','completion parity passed\n')]:
        body=(FIX/(name+'.c')).read_text();old=common
        if name=='default_capacity':
            old='''#ifndef _WIN32
#define _DEFAULT_SOURCE
#define _DARWIN_C_SOURCE
#endif
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>
static uint64_t fake_available=12345;
static BOOL WINAPI fake_memory(MEMORYSTATUSEX *memory){memory->ullAvailPhys=fake_available;return TRUE;}
static void WINAPI fake_info(SYSTEM_INFO *info){*info=(SYSTEM_INFO){0};info->dwPageSize=4096;info->dwNumberOfProcessors=3;}
#define GlobalMemoryStatusEx fake_memory
#define GetSystemInfo fake_info
#endif
'''+old
        if name=='failures':
            old='#ifndef _WIN32\n#define _DEFAULT_SOURCE\n#define _DARWIN_C_SOURCE\n#endif\n#include <pthread.h>\n#include <errno.h>\nstatic int fail_create(pthread_t*t,const pthread_attr_t*a,void*(*f)(void*),void*p){(void)t;(void)a;(void)f;(void)p;return EAGAIN;}\n#define pthread_create fail_create\n'+old
        if name in ['readiness','completion']:
            group='readiness_runtime'if name=='readiness'else'completion_runtime'
            body=body.replace('/* RUNTIME_REACTOR */',''.join((ROOT/'runtime'/path).read_text()for path in SECTIONS[group]))
        old+=body
        for opt in ['0','2']:
            results=[]
            for implementation,text in [('c',old),('corbo',replace(old,compiled))]:
                source=out/f'{name}-{implementation}-O{opt}.c';source.write_text(text);exe=source.with_suffix('.exe')
                command=[*shlex.split(a.cc),'-std=c11','-pthread','-O'+opt,'-fsanitize=undefined','-fno-sanitize-recover=all',source,'-lm','-o',exe]
                r=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180)
                assert r.returncode==0,(name,implementation,r.stderr[:3500])
                r=subprocess.run([*shlex.split(a.runner),str(exe)],capture_output=True,text=True,timeout=60)
                result=(r.returncode,r.stdout,r.stderr);assert result==(0,expected,''),(name,implementation,opt,result)
                results.append(result);print(name,implementation,'O'+opt,'passed',flush=True)
            assert results[0]==results[1];rows.append({'case':name,'optimization':opt,'parity':True})
    boundaries=json.loads((FIX/'boundaries.json').read_text());boundary_rows=[]
    for name,body in boundaries.items():
        old=common+'int main(void){'+body+'return 0;}\n';results=[]
        for implementation,text in [('c',old),('corbo',replace(old,compiled))]:
            source=out/f'boundary-{name}-{implementation}.c';source.write_text(text);exe=source.with_suffix('.exe')
            r=subprocess.run([*shlex.split(a.cc),'-std=c11','-pthread','-O2','-fsanitize=undefined','-fno-sanitize-recover=all',str(source),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=180)
            assert r.returncode==0,(name,r.stderr[:2000])
            r=subprocess.run([*shlex.split(a.runner),str(exe)],capture_output=True,text=True,timeout=60);results.append((r.returncode,r.stdout,r.stderr))
        assert results[0]==results[1] and results[0][0]!=0,(name,results)
        boundary_rows.append({'case':name,'status':results[0][0],'parity':True});print('boundary',name,'matched',flush=True)
    report={'platform':sys.platform,'reference_functions':inventory,'cases':rows,'boundaries':boundary_rows,'executions':len(rows)*2+len(boundaries)*2,'all_match':True}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
