"""Check compound assignment in the Rust frontend and corboc."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from check_crust_bootstrap import FRONTEND, PACKAGE
from check_crust_packages import compile_c


ACCEPTED = (
    ("""fn main() {
        let mut value: u64 = 12;
        value += 3; value -= 1; value *= 3; value /= 2; value %= 11;
        value &= 7; value |= 8; value ^= 1; value <<= 1; value >>= 1;
        print(value);
        let mut signed: i32 = -9;
        let count: u8 = 2;
        signed >>= count;
        print(signed);
    }""", b"11\n-3\n"),
    ("""fn index() -> i64 { print(1); 0 }
    fn right() -> u8 { print(2); 3 }
    fn increment(slice: &mut [u8]) { slice[index()] += right(); }
    fn main() {
        let mut array: [u8; 1] = [10];
        array[index()] += right();
        increment(&mut array[..]);
        print(array[0]);
    }""", b"1\n2\n1\n2\n16\n"),
    ("""struct Counter { value: i64 }
    fn main() {
        let mut counter = Counter { value: 5 };
        counter.value += 1;
        let reference = &mut counter;
        (*reference).value *= 2;
        print((*reference).value);
        let mut number = 5;
        let mut first = &mut number;
        *first += *first;
        let second = &mut first;
        **second += 2;
        print(**second);
    }""", b"12\n12\n"),
    ("""fn main() {
        let mut values = [10, 20];
        values[0] += { values[1] = 5; values[0] };
        print(values[0]); print(values[1]);
    }""", b"20\n5\n"),
    ("""struct Pair { first: i64, second: i64 }
    fn main() {
        let mut pair = Pair { first: 10, second: 20 };
        pair.first += { pair.second += 5; pair.first };
        print(pair.first); print(pair.second);
        let reference = &mut pair;
        (*reference).first += { (*reference).second *= 2; (*reference).first };
        print((*reference).first); print((*reference).second);
    }""", b"20\n25\n40\n50\n"),
    ("""async fn right(index: &mut i64) -> i64 { yield; *index = 1; 3 }
    async fn work() {
        let mut values = [10, 20];
        let mut index = 0;
        values[index] += right(&mut index).await;
        print(index); print(values[0]); print(values[1]);
    }
    fn main() { let handle = runtime::spawn(work()); drop(handle.join()); }
    """, b"1\n13\n20\n"),
    ("""struct Number { real: f32 }
    fn main() {
        let mut n = 2;
        let borrow = &n;
        n += *borrow;
        print(n);
        let mut value = Number { real: 1.25 };
        value.real *= 2.0;
        value.real %= 2.0;
        print(value.real);
        let mut index: usize = 4;
        index ^= 8;
        index <<= 1;
        print(index);
    }""", b"4\n0.5\n24\n"),
    ("""async fn step(value: f32) -> f32 { yield; value + 1. }
    async fn work() -> f32 {
        let mut values: [f32; 2] = [3., 4.];
        let value = step(.5).await;
        values[1] += { values[0] = 7.25; step(value).await };
        print(values[0]);
        values[1]
    }
    fn main() {
        let handle = runtime::spawn(work());
        match handle.join() { Ok(value) => { print(value); }, Err(_) => {}, }
    }""", b"7.25\n6.5\n"),
)

TRAPS = (
    ("fn right()->u8 {2} fn main(){let mut n:u8=255; n+=right();}", b"", b"arithmetique"),
    ("fn right()->i64 {0} fn main(){let mut n:i64=9; n/=right();}", b"", b"arithmetique"),
    ("fn right()->i64 {-1} fn main(){let mut n:i64=-9223372036854775808; n/=right();}", b"", b"arithmetique"),
    ("fn right()->i64 {-1} fn main(){let mut n:u8=9; n<<=right();}", b"", b"arithmetique"),
    ("fn right()->u8 {1} fn main(){let mut n:u8=128; n<<=right();}", b"", b"arithmetique"),
    (
        "fn idx()->i64 {print(1);8} fn rhs()->i64 {print(2);0} "
        "fn main(){let mut a=[10];a[idx()]+=rhs();}",
        b"1\n", b"indice hors du tableau",
    ),
)

REJECTED = (
    "fn main(){let n=1; n+=2;}",
    "fn main(){let mut n=1; n+=true;}",
    "fn main(){let mut n=true; n&=false;}",
    "fn main(){let mut n:u8=1; n<<=8;}",
    "fn main(){let mut n:i64=1; n>>=-1;}",
    "fn main(){let mut n=1; n%=0;}",
    "fn main(){let mut n=1; n+={n=2; 3};}",
    "fn main(){let mut a=[10,20]; a[0]+={a[0]=5; 2};}",
    "struct Item { x:i64 } fn main(){let mut a=Item{x:1}; a.x+={a.x+=1;2};}",
    "struct Item { x:i64 } fn main(){let mut a=Item{x:1}; let p=&mut a; (*p).x+={(*p).x+=1;2};}",
    "fn main(){let mut n=1; let other=n; n+=2; print(other);}",
    "fn mutate(p:&mut i64)->i64{*p=7;3} fn main(){let mut n=1; n+=mutate(&mut n);}",
    """async fn mutate(p: &mut i64) -> i64 { yield; *p = 7; 3 }
    async fn work() { let mut n = 1; n += mutate(&mut n).await; }
    fn main() { let handle = runtime::spawn(work()); drop(handle.join()); }""",
    "fn main(){let mut n=1; let p=&n; n|=2; print(*p);}",
)


def emit(frontend, compiler, source, directory):
    path = directory / "compound.crb"
    path.write_text(source)
    for command in ([frontend, "emit-c"], [compiler, "--emit-c", path]):
        yield subprocess.run(command, input=source.encode(), capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path)
    parser.add_argument("--frontend", type=Path, default=FRONTEND)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="crust-compound-") as temporary:
        directory = Path(temporary)
        compiler = args.bootstrap or directory / "corboc"
        if args.bootstrap is None:
            subprocess.run([args.frontend, "build", PACKAGE, "-o", compiler], check=True)
        generated = directory / "compound.c"
        binary = directory / "compound"
        for source, output, trap in (
            *((source, output, b"") for source, output in ACCEPTED),
            *TRAPS,
        ):
            for result in emit(args.frontend, compiler, source, directory):
                assert result.returncode == 0, (source, result.stderr, result.stdout[:160])
                generated.write_bytes(result.stdout)
                compile_c(generated, binary, ubsan=True)
                program = subprocess.run([binary], capture_output=True, timeout=10)
                assert (program.returncode != 0) == bool(trap), (source, program)
                assert program.stdout == output, (source, program)
                assert (trap in program.stderr) if trap else not program.stderr, (source, program)
                assert b"runtime error:" not in program.stderr, (source, program)
        for source in REJECTED:
            rust, crust = emit(args.frontend, compiler, source, directory)
            assert rust.returncode and crust.returncode == 8, (source, rust, crust)
    print(f"Both compilers passed {len(ACCEPTED)} executions, {len(TRAPS)} runtime traps, and {len(REJECTED)} refusals")


if __name__ == "__main__":
    main()
