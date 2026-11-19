"""Compare representations derived from the validated program AST corpus."""
import argparse
from itertools import zip_longest
from pathlib import Path
import subprocess
import tempfile

from check_crust_bootstrap import FRONTEND, PACKAGE, crust_ast, rust_ast
from check_crust_parser import corpus

REGRESSIONS = (
    'extern "C" fn first(value: i64); extern "C" fn next(value: i64); '
    'fn main() { let read = || { value }; }',
    'fn main() { move _; }',
    'fn main() { let mut value: i64 = 1; '
    '{ move value; let nested = || { @unchecked { @asm { mov ${value}, 1 } } }; } }',
    'fn f() { let x = 1; while || { x } {} }',
    'fn f() { let v = 1; loop { let a = || { return v; }; break; } }',
    'fn f() { let a = 1; let (mut x, y): (i64, i64) = (a, x); }',
)

SECTIONS = ("AST", "static nodes", "captures", "operands", "scope ends")


def compare(bootstrap, work):
    cases = {}
    for label, source in corpus():
        if len(source.encode()) <= 131072:
            cases.setdefault(source, label)
    for index, source in enumerate(REGRESSIONS):
        cases[source] = f"static fixture {index}"
    requests = "".join(f"ast\t{source.encode().hex()}\n" for source in cases)
    selection = subprocess.run([FRONTEND, "--batch"], input=requests, text=True,
                               capture_output=True, check=True)
    assert not selection.stderr, selection.stderr
    path = work / "input.crb"
    matches = 0
    for (source, label), verdict in zip(cases.items(), selection.stdout.splitlines(), strict=True):
        if not verdict.startswith("OK"):
            assert source not in REGRESSIONS, (label, verdict)
            continue
        path.write_text(source)
        result = subprocess.run([bootstrap, path], text=True, capture_output=True, timeout=15)
        assert (result.returncode, result.stderr) == (0, ""), (label, result.returncode, result.stderr)
        actual = crust_ast(result.stdout)
        expected = rust_ast(source)
        for name, observed, reference in zip(SECTIONS, actual, expected, strict=True):
            if observed != reference:
                if isinstance(observed, list):
                    index, pair = next((i, pair) for i, pair in enumerate(zip_longest(observed, reference))
                                       if pair[0] != pair[1])
                    raise AssertionError((label, name, index, *pair))
                raise AssertionError((label, name, observed, reference))
        matches += 1
    print(f"{matches} static trees matched Rust after program AST selection")


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
