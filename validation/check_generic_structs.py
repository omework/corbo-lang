"""Check constrained record specialization and its ordinary ownership rules."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
RUST = ROOT / "build/rust_frontend/debug/corbo-frontend"

SOURCE = """
struct Counter { value: i64 }
impl Counter {
    fn next(&mut self) -> Option<i64> {
        let previous = (*self).value;
        let value = &mut (*self).value;
        *value = copy(previous) + 1;
        Some(previous)
    }
    fn extra(&self) -> i64 { (*self).value }
}
#(type: V *)
#(type: T<V> with { fn next(&mut self) -> Option<V>; })
struct Cursor<T, V> { source: &mut T }
impl Cursor<T, V> {
    fn new(source: &mut T) -> Cursor<T, V> { Cursor { source: source } }
    fn next(&mut self) -> Option<V> {
        let source = &mut *(*self).source;
        source.next()
    }
}
fn main() {
    let mut counter = Counter { value: 41 };
    let mut cursor = Cursor::new(&mut counter);
    BEFORE
    match cursor.next() { Some(value) => { print(value); }, None => {} }
    print(counter.value);
}
"""

FIXED = """
struct Number { value: i64 }
impl Number { fn get(&self) -> i64 { (*self).value } }
#(type: T with { fn get(&self) -> i64; })
struct View<T> { source: &T }
impl View<T> {
    fn new(source: &T) -> View<T> { View { source: source } }
    fn get(&self) -> i64 {
        let source = &*(*self).source;
        source.get()
    }
}
fn main() {
    let number = Number { value: 7 };
    let view = View::new(&number);
    print(view.get());
}
"""

MULTIPLE = """
#(type: T *)
struct Pair<T> { left: &mut T, right: &mut [u8] }
impl Pair<T> {
    fn new(left: &mut T, right: &mut [u8]) -> Pair<T> {
        Pair { right: right, left: left }
    }
}
struct Number { value: i64 }
fn main() {
    let mut number = Number { value: 7 };
    let mut bytes: [u8; 1] = [0];
    let pair = Pair::new(&mut number, &mut bytes[..]);
    drop(pair);
    print(number.value);
    bytes[0] = 3;
    print(bytes[0]);
}
"""

ASYNC = """
struct Source { value: u8 }
impl Source {
    async fn read(&mut self, buffer: &mut [u8]) -> Result<usize, bool> {
        yield;
        buffer[0] = (*self).value;
        Ok(1)
    }
}
#(type: E *)
#(type: T<E> with { async fn read(&mut self, buffer: &mut [u8]) -> Result<usize, E>; })
struct AsyncReader<T, E> { source: &mut T, buffer: &mut [u8] }
impl AsyncReader<T, E> {
    async fn new(source: &mut T, buffer: &mut [u8]) -> AsyncReader<T, E> {
        AsyncReader { source: source, buffer: buffer }
    }
    async fn read(&mut self) -> Result<usize, E> {
        let source = &mut *(*self).source;
        let buffer = &mut *(*self).buffer;
        source.read(buffer).await
    }
}
async fn run() -> i32 {
    let mut source = Source { value: 9 };
    let mut bytes: [u8; 1] = [0];
    {
        let mut reader = AsyncReader::new(&mut source, &mut bytes[..]).await;
        match reader.read().await { Ok(count) => { print(count); }, Err(error) => { drop(error); return 1; } }
    }
    print(bytes[0]);
    0
}
fn main() {
    let execution = runtime::spawn(run());
    match execution.join() { Ok(status) => { print(status); }, Err(error) => { drop(error); } }
}
"""

OWNED = """
#(type: T *)
struct Value<T> { value: T }
impl Value<T> {
    fn new(value: T) -> Value<T> { Value { value: value } }
}
fn main() {
    let value = Value::new(12);
    print(value.value);
}
"""

DISJOINT = """
struct Pair { left: u8, right: u8 }
impl Pair {
    fn update(&mut self) {
        let left = &mut (*self).left;
        let right = &mut (*self).right;
        *left = 1;
        *right = 2;
    }
}
fn main() {
    let mut pair = Pair { left: 0, right: 0 };
    pair.update();
    print(pair.left);
    print(pair.right);
}
"""

ACCEPTED = (
    ("owned primitive inferred from a literal", OWNED, b"12\n"),
    ("borrowed records in a returned tuple", """
        struct Holder { value: &mut i64 }
        fn halves(left: &mut i64, right: &mut i64) -> (Holder, Holder) {
            (Holder { value: left }, Holder { value: right })
        }
        fn main() {}
    """, b""),
    ("generic record literal inference", OWNED.replace("Value::new(12)", "Value { value: 12 }"), b"12\n"),
    ("explicit constructor type arguments", OWNED.replace("Value::new(12)", "Value<i64>::new(12)"), b"12\n"),
    ("disjoint fields of a borrowed record", DISJOINT, b"1\n2\n"),
    ("structural result inference", SOURCE.replace("BEFORE", ""), b"41\n42\n"),
    ("result type satisfies a listed alternative", SOURCE.replace("BEFORE", "").replace("T<V> with", "T<V: i64, bool> with"), b"41\n42\n"),
    ("explicit concrete type", SOURCE.replace("BEFORE", "").replace(
        "let mut cursor =", "let mut cursor: Cursor<Counter, i64> ="), b"41\n42\n"),
    ("fixed method result", FIXED, b"7\n"),
    ("multiple borrowed fields", MULTIPLE, b"7\n3\n"),
    ("async structural method and captures", ASYNC, b"1\n9\n0\n"),
    ("async capture of a constructor result", ASYNC.replace(
        "async fn run() -> i32", "struct Config { status: i32 }\nfn configuration() -> Config { Config { status: 0 } }\nasync fn run(config: Config) -> i32"
    ).replace("print(bytes[0]);\n    0", "print(bytes[0]);\n    config.status").replace(
        "runtime::spawn(run())", "runtime::spawn(run(configuration()))"
    ), b"1\n9\n0\n"),
)
REFUSED = (
    ("user code cannot forge the std reactor hook", """
        async fn ready(socket: u64, write: bool) -> i64 { runtime::wait_socket(socket, write) }
        fn main() {}
    """),
    ("a returned tuple cannot hide a local referent", """
        struct Holder { value: &mut i64 }
        fn invalid(input: &mut i64) -> (Holder, Holder) {
            let mut local = 7;
            (Holder { value: input }, Holder { value: &mut local })
        }
        fn main() {}
    """),
    ("the same field stays exclusive", DISJOINT.replace(
        "let right = &mut (*self).right;", "let right = &mut (*self).left;")),
    ("source remains exclusively borrowed", SOURCE.replace("BEFORE", "print(counter.value);")),
    ("use after iterator move", SOURCE.replace("BEFORE", "drop(cursor);")),
    ("result type violates its listed alternatives", SOURCE.replace("BEFORE", "").replace("T<V> with", "T<V: bool> with")),
    ("missing required method", SOURCE.replace("BEFORE", "").replace(
        "fn next(&mut self) -> Option<i64>", "fn other(&mut self) -> Option<i64>", 1)),
    ("incompatible receiver", SOURCE.replace("BEFORE", "").replace(
        "#(type: T<V> with { fn next(&mut self)", "#(type: T<V> with { fn next(&self)")),
    ("exact contract rejects extra methods", SOURCE.replace("BEFORE", "").replace("T<V> with", "T<V>")),
    ("async contract rejects a sync implementation", ASYNC.replace(
        "async fn read(&mut self, buffer: &mut [u8]) -> Result<usize, bool>",
        "fn read(&mut self, buffer: &mut [u8]) -> Result<usize, bool>",
    ).replace("        yield;\n", "")),
    ("body requires an undeclared method", SOURCE.replace("BEFORE", "").replace(
        "source.next()", "source.extra(); source.next()")),
)


def run(root, program, compiler):
    if compiler is None:
        return subprocess.run([RUST, "emit-c"], input=program.encode(), capture_output=True)
    path = root / "main.crb"
    path.write_text(program)
    return subprocess.run([compiler, "--emit-c", path], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corboc", type=Path)
    parser.add_argument("--native-only", action="store_true", help="validate corboc without invoking the frozen bootstrap")
    args = parser.parse_args()
    if args.native_only and not args.corboc:
        parser.error("--native-only requires --corboc")
    compilers = [] if args.native_only else [("Rust", None)]
    if args.corboc:
        compilers.append(("corboc", args.corboc.resolve()))
    with tempfile.TemporaryDirectory(prefix="corbo-generic-structs-tests-") as tmp:
        root = Path(tmp)
        for label, compiler in compilers:
            for name, program, expected in ACCEPTED:
                generated = run(root, program, compiler)
                assert generated.returncode == 0, (label, name, generated.returncode, generated.stdout[-200:], generated.stderr)
                source = root / "probe.c"
                source.write_bytes(generated.stdout)
                for optimization in ("-O0", "-O2"):
                    binary = root / "probe"
                    subprocess.run(["cc", "-std=c11", "-pthread", optimization,
                                    "-fsanitize=undefined", "-fno-sanitize-recover=all",
                                    source, "-lm", "-o", binary], check=True)
                    assert subprocess.check_output([binary], timeout=10) == expected, (label, name)
                print(f"{label}: accepted {name}", flush=True)
            for name, program in REFUSED:
                rejected = run(root, program, compiler)
                assert rejected.returncode in (1, 8), (label, name, rejected.returncode, rejected.stdout, rejected.stderr)
                print(f"{label}: refused {name}", flush=True)


if __name__ == "__main__":
    main()
