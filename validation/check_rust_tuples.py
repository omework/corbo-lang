"""Validate tuple inference, whole-value moves, and destruction in generated C."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

PROGRAM = """
struct Child { n: i64 }
impl Child { fn drop(&mut self) { print((*self).n); } }

fn divide(n: i64, d: i64) -> (i64, i64) { (n / d, n % d) }
fn pixel() -> (u8, u16, bool) { (255, 256, true) }
fn use_pixel(p: (u8, u16, bool)) {
    let (red, green, enabled) = p;
    print(red); print(green); print(enabled);
}
fn relay(t: (Child, Child, u8)) -> (Child, Child, u8) { t }

fn main() {
    let (q, r) = divide(17, 5);
    print(q); print(r);
    let (a, b) = (12, 34);
    print(a); print(b);
    use_pixel(pixel());
    use_pixel((1, 512, false));

    let t: (Child, Child, u8) = (Child { n: 10 }, Child { n: 20 }, 255);
    let (first, second, n) = relay(t);
    drop(first);
    print(n);
}
"""

REFUSALS = [
    ("fn main() { let (a, b) = (1, 2, 3); }", "arity mismatch"),
    ("fn main() { let (a, a) = (1, 2); }", "duplicate tuple binding"),
    ("fn main() { let x = (1, 2); let (a, b) = x; drop(x); }", "déplacée"),
    ("fn bad() -> (u8, i64) { (256, 0) } fn main() {}", ""),
]


def main():
    generated = subprocess.run([FRONTEND, "emit-c"], input=PROGRAM, text=True,
                               capture_output=True, check=True)
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "tuple.c"
        binary = Path(temporary) / "tuple"
        source.write_text(generated.stdout)
        for optimization in ("-O0", "-O2"):
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization,
                 "-fsanitize=undefined", "-fno-sanitize-recover=all", source, "-lm", "-o", binary],
                check=True,
            )
            result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
            assert (result.returncode, result.stdout) == (
                0, "3\n2\n12\n34\n255\n256\ntrue\n1\n512\nfalse\n10\n255\n20\n"
            ), result

    for program, diagnostic in REFUSALS:
        result = subprocess.run([FRONTEND, "check"], input=program, text=True,
                                capture_output=True)
        assert result.returncode != 0 and diagnostic in result.stderr, (program, result.stderr)
    print("Tuple program passed UBSan at -O0 and -O2, four refusals confirmed")


if __name__ == "__main__":
    main()
