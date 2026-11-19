#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Build the C-compatible memory library using Corbo or the C reference."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--implementation',choices=['corbo','c'],default='corbo')
    parser.add_argument('--compiler',type=Path,default=os.environ.get('CORBOC'))
    parser.add_argument('--cc',default='cc')
    parser.add_argument('--ar',default='ar')
    parser.add_argument('--cflags',default='-O2')
    args=parser.parse_args();out=args.out.resolve()
    (out/'include').mkdir(parents=True,exist_ok=True);(out/'lib').mkdir(exist_ok=True)
    source=ROOT/'runtime/corbo_runtime.c'
    if args.implementation=='corbo':
        compiler=args.compiler
        if compiler is None:
            sys.path.insert(0,str(ROOT/'scripts'))
            from compiler_location import compiler_root
            compiler=compiler_root()/'build/install/bin/corboc'
        sys.path.insert(0,str(ROOT/'runtime/corbo'))
        from build import build
        generated=out/'generated';build(compiler,generated)
        parts=['c_runtime_header','base_runtime','pool_runtime','map_runtime','reclaim_runtime','c_runtime_api']
        source=out/'corbo_runtime.c'
        source.write_text(''.join((generated/(part+'.c.inc')).read_text()for part in parts))
    obj=out/'corbo_runtime.o';archive=out/'lib/libcorbo_runtime.a'
    subprocess.run([*shlex.split(args.cc),'-std=c11',*shlex.split(args.cflags),'-c',source,'-o',obj],check=True)
    archive.unlink(missing_ok=True)
    subprocess.run([*shlex.split(args.ar),'rcs',archive,obj],check=True)
    shutil.copy2(ROOT/'runtime/corbo_runtime.h',out/'include/corbo_runtime.h')
    print(archive)

if __name__=='__main__':main()
