#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused bounded-string, binary encoding and monotonic-time integration checks."""
import argparse
import json
import platform
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPT = {
    "binary": "4\n1\n4\n67305985\ntrue\n-42\n",
    "binary_edges": "true\n" * 9,
    "time": "true\n1\n",
    "async_time": "42\n",
    "bounded": "4\n4\n1\n195\n7\n4\n",
    "bounded_views": "2\n195\n2\n",
    "bounded_identity": "0\n4\n64\n",
    "bounded_growing": "5\n0\n",
    "bounded_pool": "5\n",
}
REJECT = ("bounded_wrong_type", "bounded_private", "bounded_lifetime", "bounded_mutation", "bounded_move", "bounded_invalid_bound", "bounded_wrong_input", "bounded_text_lifetime", "bounded_pool_lifetime", "invalid_numeric_type")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corboc", type=Path, required=True)
    p.add_argument("--keep", type=Path, default=ROOT / "build/binary-time")
    p.add_argument("--cc", default="cc")
    p.add_argument("--runner", default="")
    p.add_argument("--only", choices=tuple(ACCEPT)+REJECT, action="append")
    p.add_argument("--no-ubsan", action="store_true")
    a = p.parse_args(); a.keep.mkdir(parents=True, exist_ok=True)
    selected = a.only or list(ACCEPT)+list(REJECT); rows=[]
    for name in selected:
        pkg = a.keep/name; (pkg/"src").mkdir(parents=True, exist_ok=True)
        (pkg/"package.toml").write_text('[package]\nname="api_check"\n')
        (pkg/"src/main.crb").write_bytes((ROOT/"validation/fixtures/binary_time"/(name+".crb")).read_bytes())
        r = subprocess.run([a.corboc.resolve(), "--emit-package-c", pkg.resolve(), "--stdlib-dir", ROOT/"stdlib/src"], capture_output=True, timeout=120)
        if name in REJECT:
            assert r.returncode in (7,8), (name,r.returncode,r.stdout,r.stderr)
            rows.append({"case":name,"passed":True,"refused":r.returncode}); print("REFUSED",name,flush=True); continue
        assert r.returncode == 0, (name,r.returncode,r.stdout[:200],r.stderr)
        c = a.keep/(name+".c"); c.write_bytes(r.stdout); exe = a.keep/(name+".exe")
        flags=[] if a.no_ubsan else ["-fsanitize=undefined","-fno-sanitize-recover=all"]
        subprocess.run(shlex.split(a.cc)+["-std=c11","-pthread","-O1",*flags,str(c.resolve()),"-lm","-o",str(exe.resolve())],check=True,timeout=180)
        r = subprocess.run(shlex.split(a.runner)+[str(exe.resolve())],capture_output=True,text=True,timeout=30)
        assert r.returncode == 0 and r.stdout.replace("\r\n","\n") == ACCEPT[name], (name,r.returncode,r.stdout,r.stderr)
        rows.append({"case":name,"passed":True}); print("PASS",name,flush=True)
    (a.keep/"report.json").write_text(json.dumps({"platform":platform.platform(),"cases":rows},indent=2)+"\n")


if __name__ == "__main__":
    main()
