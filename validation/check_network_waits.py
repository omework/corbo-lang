#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""TCP split and UDP regressions plus the target's production multi-wait registry."""
import argparse,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/"scripts"))
from compiler_location import compiler_root
FIX=compiler_root()/"validation/fixtures/core_mechanisms"
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corboc',type=Path,required=True);p.add_argument('--keep',type=Path,required=True);p.add_argument('--cc',default='cc');p.add_argument('--runner',default='');p.add_argument('--registry',choices=['unix','windows']);a=p.parse_args();a.keep.mkdir(parents=True,exist_ok=True);pkg=a.keep/'package';(pkg/'src').mkdir(parents=True,exist_ok=True);(pkg/'package.toml').write_text('[package]\nname="network_regression"\n')
 def run(command,**kwargs):return subprocess.run([str(x)for x in command],capture_output=True,text=True,timeout=180,**kwargs)
 for name,expected in [('tcp','42\n1\n1\ntrue\n'),('udp','1\n1\n')]:
  source=(ROOT/f'validation/fixtures/async_network/{name}.crb').read_text();(pkg/'src/main.crb').write_text(source)
  r=run([a.corboc.resolve(),'--emit-package-c',pkg,'--stdlib-dir',ROOT/'stdlib/src']);assert r.returncode==0 and r.stdout.startswith('#'),(name,r.returncode,r.stdout,r.stderr);c=a.keep/(name+'.c');c.write_text(r.stdout)
  for opt in ['0','2']:
   exe=a.keep/(name+'-O'+opt+'.exe');r=run([*shlex.split(a.cc),'-std=c11','-pthread','-O'+opt,'-fsanitize=undefined','-fno-sanitize-recover=all',c,'-lm','-o',exe]);assert r.returncode==0,r.stderr
   r=run([*shlex.split(a.runner),exe]);assert (r.returncode,r.stdout,r.stderr)==(0,expected,''),(name,opt,r);print('executed',name,'O'+opt,flush=True)
  if name=='tcp':
   # Same program, but destroy the root while split tasks still retain it.
   source=source.replace('    match reading.join()', '    drop(connection);\n    match reading.join()',1);(pkg/'src/main.crb').write_text(source)
   r=run([a.corboc.resolve(),'--emit-package-c',pkg,'--stdlib-dir',ROOT/'stdlib/src']);assert r.returncode==8 and r.stdout.splitlines()[0] in ['4','5'],r;print('refused connection destruction during split tasks',flush=True)
 if a.registry:
  (a.keep/'network.c').write_bytes((a.keep/'tcp.c').read_bytes());c=a.keep/'registry.c';c.write_text((FIX/('kernel_registry.c'if a.registry=='unix'else'iocp_registry.c')).read_text());exe=a.keep/'registry.exe'
  r=run([*shlex.split(a.cc),'-std=c11','-pthread','-O2','-fsanitize=undefined','-fno-sanitize-recover=all',c,'-lm','-o',exe]);assert r.returncode==0,r.stderr
  r=run([*shlex.split(a.runner),exe]);expected='native multi-wait registry passed\n'if a.registry=='unix'else'native IOCP multi-request registry passed\n';assert(r.returncode,r.stdout,r.stderr)==(0,expected,''),r;print(expected.strip(),flush=True)
if __name__=='__main__':main()
