"""Exercise custom destructors through the normal compiler and generated C."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

INLINE = """
struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { child: Leaf, n: i64 }
impl Parent { fn drop(&mut self) -> Void { print((*self).n); } }
struct Plain { n: i64 }
fn relay(p: Parent) -> Parent { p }
fn main() {
    let moved = { let original = Parent { child: Leaf { n: 2 }, n: 1 }; relay(original) };
    drop(moved);
    { let implicit = Parent { child: Leaf { n: 4 }, n: 3 }; }
    drop(Plain { n: 0 });
}
"""

POOLED = """
struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { child: A<Leaf>, n: i64 }
impl Parent { fn drop(&mut self) { print((*self).n); } }
fn main() {
    let mut leaves = pool<Leaf>(1);
    let mut parents = pool<Parent>(1);
    let moved = { let original = parents.new({ child: leaves.new({ n: 2 }), n: 1 }); original };
    drop(moved);
    { let implicit = parents.new({ child: leaves.new({ n: 4 }), n: 3 }); }
}
"""

ASYNC = """
struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
async fn run(item: Leaf) { yield; drop(item); }
fn main() { let h = runtime::spawn(run(Leaf { n: 8 })); drop(h.join()); }
"""


def main():
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "program.c"
        binary = Path(temporary) / "program"
        for program, expected in [(INLINE, "1\n2\n3\n4\n"), (POOLED, "1\n2\n3\n4\n"), (ASYNC, "8\n")]:
            generated = subprocess.run([FRONTEND, "emit-c"], input=program, text=True,
                                       capture_output=True, check=True)
            source.write_text(generated.stdout)
            for optimization in ("-O0", "-O2"):
                subprocess.run(
                    ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization,
                     "-fsanitize=undefined", "-fno-sanitize-recover=all", "-pthread",
                     source, "-lm", "-o", binary], check=True,
                )
                result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
                assert (result.returncode, result.stdout) == (0, expected), result
    for program in [
        "struct Item {} impl Item { fn drop(&self) {} } fn main() {}",
        "struct Item {} impl Item { fn drop(&mut self, n: i64) {} } fn main() {}",
        "struct Item {} impl Item { fn drop(&mut self) {} fn drop(&mut self) {} } fn main() {}",
        "struct Item {} impl Item { fn drop(&mut self) {} } fn main() { let mut item = Item {}; item.drop(); }",
    ]:
        result = subprocess.run([FRONTEND, "check"], input=program, text=True, capture_output=True)
        assert result.returncode != 0, program
    print("3 destructor programs executed under UBSan at -O0 and -O2, 4 refusals confirmed")


if __name__ == "__main__":
    main()
