#!/usr/bin/env python3
"""Check page restitution and contextual pool constructors in generated C."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

CONSTRUCTORS = """
struct Point{x:i64,y:bool}
struct Box{item:A<i64>,point:Point}
fn main(){
    let mut numbers=pool<i64>(1);let mut boxes=pool<Box>(1);
    let mut points=pool<Point>(1);
    let b=boxes.new({item:numbers.new(7)});
    print(*(*b).item);print((*b).point.x);drop(b);
    let p=points.new();print((*p).y);drop(p);
    let p=points.new({});print((*p).x);drop(p);
    let p=points.new(Point{x:5});print((*p).x);drop(p);
    let p=points.new(x:8);print((*p).x);drop(p);
    let p=points.new({Point{x:9,y:true}});print((*p).y);
}
"""

FIXED = """
#(datastack:size=2M,reclaim_threshold=128K)
fn main(){
    {let v:[i64;4096]=[7;4096];print(v[4095]);}
    #(free_pages){let v:[i64;4096]=[9;4096];print(v[4095]);}
    {let v:[i64;65536]=[6;65536];print(v[65535]);}
}
"""

REGIONS = """
#(datastack:region_size=64K,region_stack_size=512K,region_reclaim_threshold=128K)
fn main(){
    let mut p=pool<Vector<i64>>(3);
    let mut a=p.new();a.push(7);
    {let mut b=p.new();b.push(8);print(b[0]);}
    #(free_pages){let mut b=p.new();b.push(9);print(b[0]);}
    {let mut b=p.new();let mut c=p.new();b.push(10);c.push(11);print(c[0]);}
    print(a[0]);
}
"""

TRANSFER = """
#(datastack:region_size=64K,region_stack_size=512K)
fn main(){
    let mut p=pool<Vector<i64>>(3);
    let a=#(stack_region:max_size=64K,count=3) #(free_pages){
        let mut first=p.new();first.push(3);
        let mut keep=p.new();keep.push(7);
        let mut last=p.new();last.push(9);
        print(first[0]);print(last[0]);
        keep
    };
    print(a[0]);drop(a);
}
"""

ASYNC = """
#(datastack:size=2M)
async fn work(){
    let mut n:i64=0;
    while n<2 {
        #(free_pages) {
            let v:[i64;8192]=[5;8192];yield;print(v[8191]);
            n=n+1;
            if n==1 {continue;}
            return;
        }
    }
}
fn main(){let h=runtime::spawn(work());drop(h.join());}
"""

TRACE = """
static inline void *test_mmap(void *address, size_t bytes, int prot, int flags,
                              int fd, off_t offset) {
    void *result = mmap(address, bytes, prot, flags, fd, offset);
    if ((flags & MAP_FIXED) && result == address)
        puts("reclaimed");
    return result;
}
#define mmap test_mmap
"""


def emit(source):
    return subprocess.run([FRONTEND, "emit-c"], input=source, text=True, capture_output=True)


def main():
    cases = [
        (CONSTRUCTORS, "7\n0\nfalse\n0\n5\n8\ntrue\n"),
        (FIXED, "7\n9\nreclaimed\n6\nreclaimed\n"),
        (REGIONS, "8\n9\nreclaimed\n11\nreclaimed\n7\n"),
        (TRANSFER, "3\n9\nreclaimed\nreclaimed\n7\n"),
        (ASYNC, "5\nreclaimed\n5\nreclaimed\n"),
    ]
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "test.c"
        binary = Path(directory) / "test"
        for program, expected in cases:
            result = emit(program)
            assert result.returncode == 0, result.stderr
            if program == CONSTRUCTORS:
                assert "->f0 =" in result.stdout and "->f1 =" in result.stdout
                assert "crust_reserve(CrustStruct1," not in result.stdout
            generated = result.stdout.replace("#include <unistd.h>", "#include <unistd.h>\n" + TRACE, 1)
            source.write_text(generated)
            for opt in ("-O0", "-O2"):
                subprocess.run([
                    "cc", "-std=c11", opt, "-pthread", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=undefined", "-fno-sanitize-recover=all", source, "-lm", "-o", binary,
                ], check=True)
                result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
                assert (result.returncode, result.stdout) == (0, expected), result
    for suffix, diagnostic in (
        ("", "initialiseur explicite"), ("{}", "initialiseur explicite"),
        ("{extra:7}", "champ inconnu"), ("{item:n.new(1),item:n.new(2)}", "plusieurs fois"),
    ):
        result = emit(f"""
            struct Box{{item:A<i64>}}
            fn main(){{let mut p=pool<Box>(1);let mut n=pool<i64>(2);drop(p.new({suffix}));}}
        """)
        assert result.returncode != 0 and diagnostic in result.stderr, result
    print(f"{len(cases)} témoins sous UBSan à -O0 et -O2, 4 refus confirmés")


if __name__ == "__main__":
    main()
