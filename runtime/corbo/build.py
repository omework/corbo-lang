#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Compile the real Corbo runtime into reusable C-backend resource sections."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from exports import EXPORTS,declaration,wrapper
ROOT=Path(__file__).resolve().parent
GROUPS={
 'mutex_primitives':'base_runtime','mutex':'base_runtime','metrics':'base_runtime','primitives':'base_runtime','memory':'base_runtime','collections':'base_runtime','reclaim':'base_runtime','api':'base_runtime',
 'thread_primitives':'native_runtime','scheduler':'task_runtime','values':'task_value_runtime','threads':'native_runtime',
 'socket_primitives':'readiness_runtime','readiness':'readiness_runtime',
 'completion_primitives':'completion_runtime','completion':'completion_runtime',
}

def closing_brace(text,opening):
    """Find the matching C closing brace while ignoring strings and comments."""
    at=opening+1;depth=1;state='code'
    while depth:
        ch=text[at];pair=text[at:at+2]
        if state in ['"',"'"]:
            if ch=='\\':at+=2;continue
            if ch==state:state='code'
        elif state=='line':
            if ch=='\n':state='code'
        elif state=='block':
            if pair=='*/':state='code';at+=2;continue
        elif pair=='//':state='line';at+=2;continue
        elif pair=='/*':state='block';at+=2;continue
        elif ch in ['"',"'"]:state=ch
        elif ch=='{':depth+=1
        elif ch=='}':depth-=1
        at+=1
    return at

def build(compiler,out):
    """Compile checked scalar Corbo runtime sources and assemble namespaced C ABI resource sections."""
    out.mkdir(parents=True,exist_ok=True);data=bytearray();files=[]
    for name,group in GROUPS.items():
        start=len(data);data.extend((ROOT/(name+'.crb')).read_bytes());data.extend(b'\n')
        files.append((start,len(data),name,group))
    source=out/'runtime.crb';source.write_bytes(data)
    def run(mode):
        """Invoke a compiler mode and report source-local context when runtime compilation fails."""
        p=subprocess.run([str(compiler.resolve()),mode,str(source)],capture_output=True,text=True,timeout=180)
        if p.returncode:
            try:
                numbers=list(map(int,p.stdout.split()));point=numbers[1]
                where=next((n,bytes(data[a:point]).count(b'\n')+1)for a,b,n,g in files if a<=point<b)
            except (ValueError,IndexError,StopIteration):where='unknown'
            raise RuntimeError(f'{mode} failed {p.returncode} at {where}: {p.stdout[:500]} {p.stderr[:500]}')
        return p.stdout
    ast=list(map(int,run('--ast').split()));nodes=[ast[i:i+7]for i in range(0,len(ast),7)]
    metadata={}
    for index,node in enumerate(nodes):
        if node[0]!=1:continue
        name=bytes(data[node[4]:node[5]]).decode();group=next(g for a,b,n,g in files if a<=node[2]<b)
        if name=='task_enqueue': group='base_runtime'
        metadata['f'+str(index)]=(name,group)
    text=run('--emit-runtime-c');(out/'runtime.c').write_text(text)
    assert not re.search(r'\bmark\d+\s*=\s*cursor',text),'implicit datastack dependency'
    def renamed(code):
        """Rewrite only generated function IDs into the runtime namespace before embedding them in applications."""
        return re.sub(r'\bf[0-9]+\b',lambda match:'crb_'+metadata[match[0]][0] if match[0] in metadata else match[0],code)
    aliases=''
    pieces={g:[]for g in set(GROUPS.values())};prototypes=[];count=0
    for match in re.finditer(r'(?m)^static (?:void|bool|u?int\d+_t|float|double) (f\d+)\([^\n;{]*\)\{',text):
        key=match[1];name,group=metadata[key];opening=match.end()-1;end=closing_brace(text,opening)
        prototypes.append(renamed(text[match.start():opening])+';\n');pieces[group].append(renamed(text[match.start():end]).replace('arithmetic_error(', 'crb_arithmetic_error(')+'\n');count+=1
    assert count==len(metadata),(count,len(metadata))
    abi=(ROOT/'corbo_runtime_abi.h').read_text().replace('#include "../memory/metrics_storage.h"', (ROOT.parent/'memory/metrics_storage.h').read_text())
    abi+='\n'+''.join(declaration(name,result,params)+';\n'for group,name,result,params in EXPORTS)
    common=abi+'\n'+aliases+'''#include <math.h>
static __attribute__((unused)) void crb_arithmetic_error(void){fputs("corbo: erreur arithmetique\\n",stderr);exit(EXIT_FAILURE);}
'''+''.join(prototypes)
    pieces['base_runtime'].insert(0,common)
    for group,name,result,params in EXPORTS:
        assert name in {n for n,g in metadata.values()},name
        pieces.setdefault(group,[]).append(wrapper(name,result,params))
    for group,parts in pieces.items():(out/(group+'.c.inc')).write_text(''.join(parts))
    (out/'c_runtime_header.c.inc').write_bytes((ROOT.parent/'corbo_runtime.h').read_bytes())
    report={'functions':count,'exports':len(EXPORTS),'source_sha256':hashlib.sha256(data).hexdigest(),'groups':{g:len(p)for g,p in pieces.items()}}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    """Parse runtime build options and retain the generated sources and manifest in the requested output directory."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compiler',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.compiler,a.out),indent=2))
if __name__=='__main__':main()
