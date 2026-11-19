#!/usr/bin/env python3
"""Exercise isolated native thread frames in the Rust backend."""

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

CASES = [
    ("one rewind after both joins", """
        #(datastack: region_size=1K)
        fn main(){
            #(stack_region: max_size=1K,count=4) {
                let first=runtime::thread({7});
                let second=runtime::thread({8});
                drop(second.join());
                drop(first.join());
                print(9);
            }
        }
    """, "9\nrewind 2 -> 0\n", False),
    ("rewind stops at the transferred region", """
        #(datastack: region_size=1K)
        fn main(){
            let mut p=pool<Vector<i64>>(2);
            let mut a=#(stack_region: max_size=1K,count=4) {
                let first=runtime::thread({7});
                let mut saved=p.new();saved.push(12);
                let second=runtime::thread({8});
                drop(second.join());
                drop(first.join());
                print(9);
                saved
            };
            let mut next=p.new();next.push(42);
            a.push(13);
            print(a[0]);print(a[1]);print(next[0]);
        }
    """, "9\nrewind 3 -> 2\n12\n13\n42\n", False),
    ("worker vector and live caller region", """
        #(datastack: region_stack_size=2K,region_size=1K)
        fn main(){
            let mut p=pool<Vector<i64>>(1);let mut a=p.new();a.push(5);
            let r=runtime::thread({
                let mut p=pool<Vector<i64>>(1);let mut b=p.new();b.push(12);b[0]
            }).join();
            match r{Ok(n)=>{print(n);},Err(_)=>{print(0);}}
            print(a[0]);
        }
    """, "12\n5\n", False),
    ("one frame slot is reused after each join", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn main(){
            let mut n:i64=0;
            while n<40 {
                let r=runtime::thread({7}).join();
                match r{Ok(value)=>{n=n+value-6;},Err(_)=>{n=1000;}}
            }
            print(n);
        }
    """, "40\n", False),
    ("independent inferred bounds and nested worker", """
        fn initial()->i64 {let a:[i64;8]=[3;8];a[0]}
        fn main(){
            let r=runtime::thread({
                let mut p=pool<Vector<i64>>(1);let mut a=p.new();a.push(initial());
                let r=runtime::thread({initial()+1}).join();
                match r {Ok(n)=>{n+a[0]},Err(_)=>{0}}
            }).join();
            match r {Ok(n)=>{print(n);},Err(_)=>{print(0);}}
        }
    """, "7\n", False),
    ("failed launch releases frame before retry", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn main(){
            let a=runtime::thread({print(99);}).join();
            match a{Ok(())=>{print(0);},Err(_)=>{print(1);}}
            let b=runtime::thread({print(7);}).join();
            match b{Ok(())=>{print(2);},Err(_)=>{print(0);}}
        }
    """, "1\n7\n2\n", True),
    ("owned vector moves through native thread and join", """
        fn main(){
            let mut p=pool<Vector<i64>>(1);
            let h=#(stack_region:max_size=4K,count=2){
                let mut v=p.new();v.push(7);
                runtime::thread({move v;let mut v=v;v.push(9);v})
            };
            match h.join(){Ok(v)=>{print(v[0]);print(v[1]);drop(v);},Err(_)=>{print(0);}}
        }
    """, "7\n9\n", False),
    ("failed native launch destroys a captured ownership tree", """
        struct Boxed{leaf:A<i64>}
        fn main(){
            let mut leaves=pool<i64>(1);let mut boxes=pool<Boxed>(1);
            let b=boxes.new(Boxed{leaf:leaves.new(6)});
            let h=runtime::thread({move b;print(*(*b).leaf);});
            match h.join(){Ok(())=>{print(0);},Err(_)=>{print(1);}}
            let b=boxes.new(Boxed{leaf:leaves.new(7)});print(*(*b).leaf);
        }
    """, "1\n7\n", True),
    ("named scalar captures move into the frame", """
        fn main(){
            let n:i64=7;let m:i32=3;
            let r=runtime::thread({move n;move m;print(m);n+1}).join();
            match r{Ok(n)=>{print(n);},Err(_)=>{print(0);}}
        }
    """, "3\n8\n", False),

]

FAILED_CREATE = r"""
static int test_pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                               void *(*start)(void *), void *argument) {
    static int attempts;
    if (attempts++ == 0)
        return 1;
    return pthread_create(thread, attr, start, argument);
}
#define pthread_create test_pthread_create
"""


def emit(source):
    return subprocess.run([FRONTEND, "emit-c"], input=source, text=True, capture_output=True)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "test.c"
        binary = Path(temporary) / "test"
        for name, program, expected, inject_failure in CASES:
            result = emit(program)
            assert result.returncode == 0, (name, result.stderr)
            generated = result.stdout
            assert "CrustThreadFrame" in generated and "crust_region_release(&handle->region);" in generated
            if name in ("one rewind after both joins", "rewind stops at the transferred region"):
                cursor_store = "        band->cursor = cursor;"
                assert generated.count(cursor_store) == 1
                trim = "static void crust_region_trim(CrustRegionBand *band) {"
                assert trim in generated
                generated = generated.replace(
                    trim, "static _Thread_local const unsigned char *transferred_address;\n" + trim
                )
                generated = generated.replace(cursor_store, r"""
        {
            if (band->count == 4 && band->limit == 1024) {
                printf("rewind %zu -> %zu\n", band->cursor, cursor);
                if (cursor != 0)
                    transferred_address = band->data + (cursor - 1) * band->stride;
            }
            band->cursor = cursor;
        }
""")
                append = "    if (count > value->band->limit - value->used)"
                assert append in generated
                generated = generated.replace(append, r"""
    if (value->used != 0 && transferred_address != NULL &&
        crust_region_data(value) != transferred_address)
        abort();
""" + append)
            if name == "owned vector moves through native thread and join":
                append = "    if (count > value->band->limit - value->used)"
                element = "    if (index >= value->used / size)"
                anchor = "static inline __attribute__((unused)) void crust_region_append("
                assert all(marker in generated for marker in (append, element, anchor))
                generated = generated.replace(anchor, "static const void *test_data;\n" + anchor)
                generated = generated.replace(append, """
    if (value->used == 0)
        test_data = crust_region_data(value);
    else if (test_data != crust_region_data(value))
        abort();
""" + append)
                generated = generated.replace(element, """
    if (test_data != crust_region_data(value))
        abort();
""" + element)
            if inject_failure:
                generated = generated.replace("#include <pthread.h>", "#include <pthread.h>\n" + FAILED_CREATE, 1)
            source.write_text(generated)
            for optimization in ("-O0", "-O2"):
                subprocess.run(
                    [
                        "cc", "-std=c11", optimization, "-pthread", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        source, "-lm", "-o", binary,
                    ],
                    check=True,
                )
                result = subprocess.run([binary], text=True, capture_output=True)
                assert result.returncode == 0 and result.stdout == expected, (name, result)
            print(f"{name} OK")

    for program, diagnostic in [
        ("fn main(){let n:i64=1;drop(runtime::thread({n}).join());}", "non initialisée"),
        ("fn main(){let n:i64=1;let r=&n;drop(runtime::thread({move r;*r}));}",
         "ne peut pas être abandonné"),
        ("fn main(){let n:i64=1;drop(runtime::thread({move n;n}).join());print(n);}",
         "déjà déplacée"),
        ("fn main(){drop(runtime::thread({yield;}).join());}", "hors du sous-ensemble"),
        ("""fn main(){
            let h={
                let mut p=pool<i64>(1);let a=p.new(7);
                runtime::thread({move a;*a})
            };
            drop(h.join());
        }""", "la dépendance ne survit pas à la sortie du bloc"),
    ]:
        result = emit(program)
        assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
    print("5 refus confirmés")


if __name__ == "__main__":
    main()
