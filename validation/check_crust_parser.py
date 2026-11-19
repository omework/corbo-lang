"""Compare standalone Crust and Rust program ASTs before static analysis."""
import argparse
import ast
from itertools import zip_longest
from pathlib import Path
import re
import subprocess
import tempfile
from textwrap import dedent

from check_crust_bootstrap import FRONTEND, INVALID, KINDS, PACKAGE, ROOT, VALID, syntax_rows

PROGRAM = re.compile(r"(?:^|\n)\s*(?:#\(|(?:(?:pub|async)\s+)*(?:fn|struct|enum|impl|use|extern)\s+)")
FENCE = re.compile(r"^```(?:crust|rust)[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)

REGRESSIONS = (
    "fn f(){let mut x = 1; x &= 2; x |= 3; x ^= 4; x <<= 1; x >>= 2;}",
    "fn f(){let x: Vector<Vector<i64>>=y;}",
    "fn f(){x >> = y;}",

    "fn a(){ if Flag {} {} }",
    "fn a(){ match F {} { _ => {} } }",
    "fn a(){ match E.V {} { _ => {} } }",
    "fn a(){ while Flag {} {} }",
    "fn a(){ if Flag {} else {} }",
    "fn a(){ if !!!Flag {} }",
    "fn a(){ if a && Flag {} }",
    "fn a(){ if Flag {} && a {} }",
    "fn a(){ x.lower { n: 1 }; }",
    "fn a(){ X.Y.Z { n: 1 }; }",
    "fn a(){ x().Y { n: 1 }; }",
    "fn a(){ x.async(); a.yield; a.match; a.fn; }",
    "fn a(){ let async = 1; print(async); }",
    "fn a(yield: i64){ yield; }",
    "fn a(use: i64){ use; }",
    "fn a(){ let _ = x; }",
    "fn a(){ let i64 = x; }",
    "fn f(_ : i64) {}",
    "struct Vector {}",
    "fn f(){ @unchecked #(free_pages) { @asm { nop } } }",
    "fn f(){ move #(free_pages) { } }",
    "fn f(){ move #(stack_region: max_size=4M) { } }",
    "fn f(){ x.try_slice(1, 2..3); }",
    "fn f(){ x.try_slice(.., ..3); }",
    "fn f(){ if a {} else if c {}.field; }",
    "fn f(){ a::b::fn(); }",
    "fn f(){ let x = |&self| {}; }",
    "extern C fn f();",
    'extern "C" fn f(x: i64) -> ();',
    '#(lock: on=self) extern "C" fn f();',
    "fn f(){ match x { A::Ok(true) => {} } }",
    "fn f(){ match x { E.V { async: yield } => {} } }",
    "use f::{async, await, yield as run};",
    "use f::a as Vector;",
    "#(directive: stack_region_max_size=1K)",
    "fn f(){let f=|| #(directive: stack_region_max_size=1K) {};}",
)


def corpus():
    for index, source in enumerate((*VALID, *INVALID, *REGRESSIONS)):
        yield f"fixture {index}", source
    for directory in (PACKAGE, ROOT / "examples", ROOT / "validation", ROOT / "stdlib"):
        for path in sorted(directory.rglob("*.crb")):
            yield str(path.relative_to(ROOT)), path.read_text()
    documents = [ROOT / "README.md", *(ROOT / "docs").rglob("*.md"),
                 *(ROOT / "design-buffer").rglob("*.md")]
    for path in sorted(documents):
        if path.name.endswith("-fr.md"):
            continue
        for index, match in enumerate(FENCE.finditer(path.read_text()), 1):
            yield f"{path.relative_to(ROOT)} fence {index}", match[1]
    for directory in ("tests", "validation"):
        for path in sorted((ROOT / directory).glob("*.py")):
            if path.resolve() == Path(__file__).resolve():
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if PROGRAM.search(node.value):
                        yield f"{path.relative_to(ROOT)}:{node.lineno}", dedent(node.value)


def compare(bootstrap, work):
    cases = {}
    oversized = set()
    for label, source in corpus():
        if len(source.encode()) <= 131072:
            cases.setdefault(source, label)
        else:
            oversized.add(source)
    requests = "".join(f"ast\t{source.encode().hex()}\n" for source in cases)
    result = subprocess.run([FRONTEND, "--batch"], input=requests, text=True, capture_output=True, check=True)
    assert not result.stderr, result.stderr
    path = work / "input.crb"
    accepted = rejected = 0
    mismatches = []
    for (source, label), response in zip(cases.items(), result.stdout.splitlines(), strict=True):
        path.write_text(source)
        run = subprocess.run([bootstrap, "--ast", path], capture_output=True, timeout=15)
        status, *parts = response.split("\t")
        if status == "ERR" and run.returncode in (3, 7) and not (run.stdout or run.stderr):
            rejected += 1
            continue
        if status != "OK" or run.returncode != 0 or run.stderr:
            mismatches.append((label, status, parts[:2], run.returncode, run.stderr[:400]))
            continue
        expected = [(KINDS.index(kind), *map(int, fields))
                    for kind, *fields in (node.split(":") for node in parts)]
        actual, _ = syntax_rows(list(map(int, run.stdout.split())))
        if actual != expected:
            index, pair = next((i, pair) for i, pair in enumerate(zip_longest(actual, expected))
                               if pair[0] != pair[1])
            mismatches.append((label, f"node {index}", *pair))
        else:
            accepted += 1
    print(f"{accepted} ASTs matched Rust, {rejected} inputs rejected by both, "
          f"{len(oversized)} distinct inputs above 128 KiB")
    assert not mismatches, "\n" + "\n".join(map(str, mismatches))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--bootstrap", type=Path, help="run an existing bootstrap executable")
    args = cli.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        bootstrap = args.bootstrap
        if bootstrap is None:
            generated = work / "bootstrap.c"
            bootstrap = work / "bootstrap"
            with generated.open("w") as output:
                subprocess.run([FRONTEND, "emit-c", PACKAGE], stdout=output, check=True)
            subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                            "-fno-sanitize-recover=all", generated, "-o", bootstrap], check=True)
        compare(bootstrap.resolve(), work)


if __name__ == "__main__":
    main()
