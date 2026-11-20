#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
from pathlib import Path
import subprocess,json
import argparse
p = argparse.ArgumentParser(description='Direct constant/generic regressions for bounded-string integration.')
p.add_argument('--corboc', type=Path, required=True)
a = p.parse_args()
root=Path(__file__).resolve().parents[1];out=root/'build/binary-time-related';out.mkdir(parents=True,exist_ok=True)
cases={'constant':('const WIDTH: usize = 4;\nfn main() { let values: [u8; WIDTH] = [0; WIDTH]; print(values[0]); }','0\n'),'generic':('#(type: T)\nstruct Boxed<T> { value: T }\nimpl Boxed<T> { fn new(value: T) -> Boxed<T> { Boxed { value: value } } }\nfn main() { let a = Boxed::new(42); let b = Boxed::new(true); print(a.value); print(b.value); }','42\ntrue\n')}
rows=[]
for name,(source,expected) in cases.items():
 p=out/name;(p/'src').mkdir(parents=True,exist_ok=True);(p/'package.toml').write_text('[package]\nname="related"\n');(p/'src/main.crb').write_text(source)
 r=subprocess.run([a.corboc.resolve(),'--emit-package-c',p,'--stdlib-dir',root/'stdlib/src'],capture_output=True);assert r.returncode==0,(name,r.returncode,r.stdout,r.stderr);c=out/(name+'.c');c.write_bytes(r.stdout);exe=c.with_suffix('.exe');subprocess.run(['cc','-O1','-fsanitize=undefined','-fno-sanitize-recover=all',c,'-o',exe],check=True);r=subprocess.run([exe],capture_output=True,text=True);assert r.returncode==0 and r.stdout==expected,(name,r.returncode,r.stdout,r.stderr);rows.append(dict(case=name,passed=True));print('PASS',name,flush=True)
(out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
