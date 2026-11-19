"""Exercise Crust operands, address provenance, and target-sized integers."""
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"
LINUX64 = "x86_64-unknown-linux-musl"
LINUX32 = "i686-unknown-linux-gnu"

PROGRAM = """
fn main() {
    let mut buffer: [u8; 2] = [0, 0];
    let fd: i64 = 0;
    let length: usize = 2;
    let mut output: i64 = 0;
    print(buffer[0]);
    @unchecked {
        let address: usize = addr(&buffer[0]);
        @asm {
            pushfq
            push rax
            push rcx
            push r11
            push rdi
            push rsi
            push rdx
            mov rdi, ${fd}
            mov rsi, ${address}
            mov rdx, ${length}
            xor eax, eax
            syscall
            mov ${output}, rax
            pop rdx
            pop rsi
            pop rdi
            pop r11
            pop rcx
            pop rax
            popfq
        }
    }
    print(output);
    print(buffer[0]);
}
"""

REFUSALS = [
    (LINUX64, "fn main() { @asm { nop } }", "exige un bloc @unchecked"),
    ("riscv64-unknown-linux-gnu", "fn main() { @unchecked { @asm { nop } } }", "indisponible pour cette cible"),
    (LINUX64, "fn main() { @unchecked { let x = 1; drop(x); print(x); } }", "déplacée"),
    (LINUX64, "fn main() { @unchecked { let p = addr(12); drop(p); } }", "exige une référence"),
    (LINUX64, "fn main() { @unchecked { @asm { mov rax, ${missing} } } }", "liaison assembleur inconnue"),
    (LINUX64, "fn main() { let x = 1; @unchecked { @asm { mov ${x}, rax } } }", "liaison mutable"),
    (LINUX64, "fn main() { let x = 1; drop(x); @unchecked { @asm { mov rax, ${x} } } }", "déplacée"),
    (LINUX64, """fn main() { let x = 1; @unchecked {
        let address = addr(&x);
        let p = copy(address) + 0;
        drop(x);
        @asm { mov rax, ${p} }
    } }""", "emprunt actif"),
    (LINUX64, "fn main() { let x = 1; let p = addr(&x); drop(p); }", "exige un bloc @unchecked"),
    (LINUX64, "fn bad(x: &i64) -> usize { @unchecked { return addr(x); } } fn main() {}", "ne peut pas sortir"),
    (LINUX64, "fn main() { let mut p: usize = 0; let x = 1; @unchecked { p = addr(&x); } print(p); }", "ne peut pas sortir"),
    (LINUX64, """struct Pointer { address: u64 }
fn main() { let mut output = Pointer { address: 0 }; let x = 1; @unchecked {
    let address = addr(&x);
    let duplicate = copy(address);
    output = Pointer { address: duplicate as u64 };
} drop(output); }""", "ne peut pas sortir"),
    (LINUX32, "fn main() { let n: usize = 4294967296; print(n); }", "hors limites"),
]


def compile_crust(source, action, target, package=None):
    args = [FRONTEND, action, "--target", target]
    if package:
        args = [FRONTEND, action, package, "--target", target]
    return subprocess.run(args, input=source, capture_output=True, text=True, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="cc", help="Linux x86-64 C compiler command")
    parser.add_argument("--binaries", type=Path, help="Keep ELF witnesses in this directory for external execution")
    args = parser.parse_args()

    for target, source, diagnostic in REFUSALS:
        result = compile_crust(source, "check", target)
        assert result.returncode == 1 and diagnostic in result.stderr, (source, result.stderr)

    for target, limit in [(LINUX32, 4294967295), (LINUX64, 18446744073709551615)]:
        result = compile_crust(f"fn main() {{ let n: usize = {limit}; print(n); }}", "emit-c", target)
        assert result.returncode == 0, result.stderr
        bits = 32 if target == LINUX32 else 64
        assert f"sizeof(uintptr_t) * CHAR_BIT == {bits}" in result.stdout

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        direct = compile_crust(PROGRAM, "emit-c", LINUX64)
        assert direct.returncode == 0, direct.stderr
        (root / "package.toml").write_text('[package]\nname = "asm_probe"\n')
        (root / "src").mkdir()
        (root / "src/main.crb").write_text(PROGRAM)
        packaged = compile_crust(None, "emit-c", LINUX64, root)
        assert packaged.returncode == 0, packaged.stderr
        if args.binaries:
            args.binaries.mkdir(parents=True, exist_ok=True)
        for optimization, generated in [("O0", direct.stdout), ("O2", packaged.stdout)]:
            source = root / "probe.c"
            source.write_text(generated)
            binary = (args.binaries or root) / f"probe-{optimization}"
            subprocess.run([*shlex.split(args.cc), "-std=c11", "-Wall", "-Wextra",
                            "-Werror", f"-{optimization}", source, "-o", binary], check=True)
            if not args.binaries:
                result = subprocess.run([binary], input="AB", capture_output=True, text=True, timeout=10)
                assert (result.returncode, result.stdout) == (0, "0\n2\n65\n"), result
    print(f"{len(REFUSALS)} refusals, both usize widths, and direct/package C compilation passed")
    if not args.binaries:
        print("Both ELF executions produced 0, 2, 65")


if __name__ == "__main__":
    main()
