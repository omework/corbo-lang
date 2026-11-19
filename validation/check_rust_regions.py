#!/usr/bin/env python3
"""Run the region layout, capacity and cleanup cases against generated C."""

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

ACCEPTED = [
    ("exclusive growth fits a fixed regional stack", """
        #(datastack: region_stack_size=1K)
        fn main(){
            let mut p=pool<String>(1);let mut text=p.new();
            if false {text.push_str("LEFT");} else {text.push_str("RIGHT");}
            print(text.byte_len());
        }
    """.replace("LEFT", "a" * 600).replace("RIGHT", "b" * 601),
     "601\n", "sizeof(uint8_t), 1, 601"),
    ("exclusive constructions transfer one live region", """
        fn build(p:&mut Pool<Vector<u8>>, flag:bool)->A<Vector<u8>> {
            if flag {p.new()} else {p.new()}
        }
        fn main(){
            let mut p=pool<Vector<u8>>(3);
            let mut first=p.new();first.push(4);
            let mut next=build(&mut p,false);next.push(8);
            print(first[0]);print(next[0]);
        }
    """, "4\n8\n", "crust_regions_configure(UINT64_C(0), region_bytes, 2)"),
    ("an unbounded loop uses dedicated regions for retained contents", """
        #(datastack: region_size=1K)
        fn main(){
            let mut strings=pool<String>(3);
            let mut vectors=pool<Vector<A<String>>>(1);
            let mut v=vectors.new();let mut n:i64=0;
            while n<3 {let s=strings.new();v.push(s);n=n+1;}
            print(v.len());
        }
    """, "3\n", "->data = crust_region_take_dedicated();"),
    ("a recursive callee uses dedicated regions without changing its caller", """
        #(datastack: region_size=1K)
        fn visit(n:i64){
            let mut p=pool<Vector<u8>>(1);let mut a=p.new();a.push(7);
            if n>0 {visit(n-1);}
            print(a[0]);
        }
        fn main(){
            let mut p=pool<Vector<u8>>(1);let mut a=p.new();a.push(9);
            visit(2);print(a[0]);
        }
    """, "7\n7\n7\n9\n", "crust_regions_configure(UINT64_C(0), UINT64_C(1024), 1)"),
    ("a different inherited gabarit has its own inferred slot count", """
        #(datastack: region_size=1K)
        fn main(){
            let mut p=pool<Vector<u8>>(3);let mut a=p.new();a.push(4);
            #(stack_region: max_size=2K) {
                let mut b=p.new();let mut c=p.new();
                b.push(8);c.push(9);print(b[0]);print(c[0]);
            }
            print(a[0]);
        }
    """, "8\n9\n4\n", "crust_region_enter(UINT64_C(2048), UINT64_C(0), 2)"),
    ("inferred layout", """
        struct Pair{x:i64,y:i64}
        fn main(){
            let mut p=pool<Vector<Pair>>(2);
            let mut a=p.new();let mut b=p.new();
            a.push(Pair{x:4,y:9});b.push(Pair{x:5,y:6});
            print(a.len());print(a[0].y);print(b[0].x);
        }
    """, "1\n9\n5\n", "crust_regions_configure(UINT64_C(0), region_bytes, 2)"),
    ("utf8 and embedded nul", r"""
        #(datastack: region_stack_size=2K, region_size=1K)
        fn main(){
            let mut p=pool<String>(1);let mut a=p.new();
            a.push_str("é\uD83D\uDE00\u0000");a.push_str("");print(a.byte_len());
        }
    """, "7\n", "crust_regions_configure(UINT64_C(2048), UINT64_C(1024), 1)"),
    ("local count, spill and transfer", """
        #(datastack: region_stack_size=1K, region_size=1K)
        fn main(){
            let mut p=pool<Vector<i64>>(2);
            let mut a=#(stack_region: max_size=2K,count=1) {
                let mut a=p.new();let mut b=p.new();
                a.push(7);b.push(8);print(b[0]);a
            };
            a.push(9);print(a[0]);print(a[1]);drop(a);
            let mut c=p.new();c.push(5);print(c[0]);
        }
    """, "8\n7\n9\n5\n", "crust_region_enter(UINT64_C(2048), UINT64_C(1), 1)"),
    ("reuse an interior slot", """
        #(datastack: region_stack_size=2K,region_size=1K)
        fn main(){
            let mut p=pool<Vector<i64>>(2);
            let mut a=p.new();let mut b=p.new();
            a.push(3);b.push(4);drop(a);let mut c=p.new();c.push(5);
            print(b[0]);print(c[0]);
        }
    """, "4\n5\n", "UINT64_C(2048), UINT64_C(1024), 2"),
    ("callee inherits region and return transfers cleanup", """
        fn build(p:&mut Pool<Vector<u8>>)->A<Vector<u8>> {
            let mut a=p.new();a.push(11);a
        }
        fn main(){
            let mut p=pool<Vector<u8>>(1);
            let a=#(stack_region: max_size=1K) {build(&mut p)};
            print(a[0]);drop(a);let b=build(&mut p);print(b[0]);
        }
    """, "11\n11\n", "crust_region_enter(UINT64_C(1024), UINT64_C(0), 1)"),
    ("continue and break restore marks", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn main(){
            let mut p=pool<Vector<u8>>(1);let mut n:i64=0;
            loop #(stack_region: max_size=2K,count=1) {
                let mut a=p.new();a.push(3);n=n+1;
                if n < 100 { continue; }
                print(a[0]);break;
            }
            let mut b=p.new();b.push(5);print(b[0]);
        }
    """, "3\n5\n", "crust_scope_rewind"),
    ("independent fallback for dynamic growth", """
        fn main(){
            let mut p=pool<Vector<i64>>(1);let mut a=p.new();let mut n:i64=0;
            while n<3 {a.push(copy(n));n=n+1;} print(a.len());
        }
    """, "3\n", "crust_regions_configure(UINT64_C(0), 0, 1)"),
]

EXHAUSTED = [
    ("global stack limit", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn main(){let mut p=pool<Vector<u8>>(2);let a=p.new();let b=p.new();drop(a);drop(b);}
    """),
    ("transferred region keeps its original limit", """
        #(datastack: region_stack_size=2K,region_size=2K)
        fn main(){
            let mut p=pool<Vector<i64>>(1);
            let mut a=#(stack_region: max_size=1K) {p.new()};
            let mut n:i64=0;while n<129 {a.push(copy(n));n=n+1;}
        }
    """),
]


def emit(source):
    return subprocess.run(
        [FRONTEND, "emit-c"], input=source, text=True, capture_output=True
    )


def main():
    with tempfile.TemporaryDirectory() as temporary:
        source_file = Path(temporary) / "test.c"
        binary = Path(temporary) / "test"
        cases = [(name, source, output, marker, 0) for name, source, output, marker in ACCEPTED]
        cases.extend((name, source, "", "", 1) for name, source in EXHAUSTED)
        for name, source, expected, marker, status in cases:
            generated = emit(source)
            assert generated.returncode == 0 and marker in generated.stdout, (name, generated.stderr)
            if name == "a recursive callee uses dedicated regions without changing its caller":
                assert generated.stdout.count("->data = crust_region_take_dedicated();") == 1
                assert generated.stdout.count("->data = crust_region_take();") == 1
            if name == "local count, spill and transfer":
                assert generated.stdout.count("->data = crust_region_take_dedicated();") == 1
            if name == "a different inherited gabarit has its own inferred slot count":
                assert "crust_regions_configure(UINT64_C(0), UINT64_C(1024), 1)" in generated.stdout
            source_file.write_text(generated.stdout)
            for opt in ("-O0", "-O2"):
                subprocess.run(
                    [
                        "cc", "-std=c11", opt, "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        source_file, "-lm", "-o", binary,
                    ],
                    check=True,
                )
                run = subprocess.run([binary], text=True, capture_output=True)
                assert run.returncode == status and run.stdout == expected, (name, run)
                if status == 1:
                    assert run.stderr == "corbo: limite de la datastack à régions\n", (name, run)
            print(f"{name} OK")
    for annotation, message in [
        ("#(stack_region: max_size=0K)", "strictement positif"),
        ("#(stack_region: max_size=1K,count=0)", "strictement positif"),
        ("#(stack_region: max_size=1Ki)", "unité"),
    ]:
        generated = emit(f"fn main(){{ {annotation} {{}} }}")
        assert generated.returncode != 0 and message in generated.stderr, generated.stderr
    print("3 annotations refusées")


if __name__ == "__main__":
    main()
