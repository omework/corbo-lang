"""Check address confinement in both compilers on the host."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

ACCEPT = """
fn main() {
    let number: [u8; 1] = [42];
    let scalar = 42;
    let reference = &scalar;
    let mut size: usize = 0;
    @unchecked {
        let address = addr(&number[0]);
        drop(address);
        let other = addr(reference);
        drop(other);
        size = 3;
    }
    print(size);
}
"""

REFUSE = [
    (1, "fn main() { let n = 1; let x = addr(&n); drop(x); }"),
    (4, "fn main() { let n = 1; let mut x: usize = 0; @unchecked { x = addr(&n); } print(x); }"),
    (4, "fn f(n: &i64) -> usize { @unchecked { return addr(n); } } fn main() {}"),
    (4, """struct Bits { address: u64 }
        fn main() {
            let n = 1;
            let mut out = Bits { address: 0 };
            @unchecked {
                let p = addr(&n);
                let duplicate = copy(p);
                out = Bits { address: duplicate as u64 };
            }
            drop(out);
        }"""),
    (4, """fn record(n: usize, out: &mut usize) { *out = n; }
        fn main() {
            let n = 1;
            let mut out: usize = 0;
            @unchecked { record(addr(&n), &mut out); }
            print(out);
        }"""),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corboc", type=Path, required=True)
    compiler = parser.parse_args().corboc.resolve()
    with tempfile.TemporaryDirectory(prefix="crust-address-") as directory:
        root = Path(directory)
        source = root / "input.crb"

        def verify(code, mode):
            source.write_text(code)
            return subprocess.run([compiler, mode, source], capture_output=True, text=True, timeout=30)

        for rule, code in REFUSE:
            rust = subprocess.run([FRONTEND, "check"], input=code, text=True, capture_output=True)
            diagnostic = "exige un bloc @unchecked" if rule == 1 else "ne peut pas sortir"
            assert rust.returncode == 1 and diagnostic in rust.stderr, rust
            for mode in ("--verify", "--emit-c"):
                native = verify(code, mode)
                assert native.returncode == 8 and native.stdout.splitlines()[0] == str(rule), native

        rust = subprocess.run([FRONTEND, "emit-c"], input=ACCEPT, text=True, capture_output=True, check=True)
        native = verify(ACCEPT, "--emit-c")
        assert native.returncode == 0, native
        for label, generated in (("rust", rust.stdout), ("corboc", native.stdout)):
            c_file = root / f"{label}.c"
            executable = root / label
            c_file.write_text(generated)
            subprocess.run(
                ["cc", "-std=c11", "-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                 "-pthread", c_file, "-lm", "-o", executable], check=True
            )
            run = subprocess.run([executable], capture_output=True, text=True, check=True, timeout=10)
            assert (run.stdout, run.stderr) == ("3\n", ""), run
    print(f"Both compilers accepted the local address and rejected {len(REFUSE)} escaping or misplaced uses")


if __name__ == "__main__":
    main()
