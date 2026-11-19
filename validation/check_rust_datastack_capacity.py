#!/usr/bin/env python3
"""Check the selected capacity against the high-water mark of generated C."""

import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

RECURSION = """
fn recur(n:i64)->i64 {
    if n == 0 { 0 } else { let k = n - 1; recur(k) + 1 }
}
fn main(){ print(recur(3)); }
"""
BRANCHES = """
fn main(){
    let tag:u8=1;
    let count:i64=2;
    if false {
        let a:[u8;32]=[1;32]; print(a[0]);
    } else {
        let b:[i64;16]=[2;16]; print(b[0]);
    }
    print(tag); print(count);
}
"""
LOOP = """
fn main(){
    let mut n:i64=0;
    while n < 20000 {
        let values:[i64;64]=[1;64];
        n=n+values[0];
    }
    print(n);
}
"""
CALL = """
struct P { x:i64 }
fn make(x:i64)->P { let extra:[i64;4]=[x;4]; P{x:extra[0]} }
fn relay(x:i64)->P { make(x) }
fn main(){ let a={relay(7)}; print(a.x); }
"""
POOL = """
enum E { Empty, Payload { x:i64 } }
fn main(){
    let mut pool=pool<E>(4);
    let value=pool.new(E.Payload{x:5});
    match &value { E.Empty=>{}, E.Payload{x:n}=>{print(n);} }
}
"""


def emit(source):
    return subprocess.run(
        [FRONTEND, "emit-c"], input=source, text=True, capture_output=True
    )


def run_c(c, directory, optimization):
    source = directory / "capacity.c"
    executable = directory / "capacity"
    cursor_update = "    crust_cursor = next;"
    assert cursor_update in c
    instrumented = c.replace(
        cursor_update, cursor_update + "\n    if (next > high_water) high_water = next;"
    )
    source.write_text(
        "#define main crust_entry\nstatic unsigned long long high_water;\n"
        + instrumented
        + r"""
#undef main
int main(void) {
    int status = crust_entry();
    fprintf(stderr, "%zu:%llu\n", crust_capacity, high_water);
    return status;
}
"""
    )
    subprocess.run(
        [
            "cc", "-std=c11", optimization, "-Wall", "-Wextra", "-Werror",
            "-fsanitize=undefined", "-fno-sanitize-recover=all",
            source, "-lm", "-o", executable,
        ],
        check=True,
    )
    return subprocess.run([executable], text=True, capture_output=True)


def main():
    cases = [
        ("aligned branches", BRANCHES, "inferred", "2\n1\n2\n", 144),
        ("loop rewind", LOOP, "inferred", "20000\n", 520),
        ("caller reservations", CALL, "inferred", "7\n", None),
        ("successive scalar moves share the final receiver slot",
         "fn main(){let a={{let x:i64=7;let y=x;let z=y;z}};print(a);}",
         "inferred", "7\n", 8),
        ("exclusive moves of one scalar share the final receiver",
         "fn main(){let a=loop{let x:i64=7;if false{break x;}else{break x;}};print(a);}",
         "inferred", "7\n", 8),
        ("one scalar can stay local or return to its caller",
         "fn pick(early:bool)->i64{let x:i64=7;if early{return x;}"
         "let local={x};print(local);8} "
         "fn main(){{print(pick(true));}{print(pick(false));}}",
         "inferred", "7\n7\n8\n", 9),
        ("one scalar feeds an inner or outer receiver",
         "fn main(){let a=loop{let x:i64=7;if false{break x;}"
         "let local={x};print(local);break 8;};print(a);}",
         "inferred", "7\n8\n", 8),
        ("nested scalar uses its final receiver slot",
         "fn main(){let a={{let n:i64=7;n}};print(a);}",
         "inferred", "7\n", 8),
        ("scalar call uses its final binding slot",
         "fn make()->i64{let x:i64=7;x} fn main(){let a=make();print(a);}",
         "inferred", "7\n", 8),
        ("nested call constructs in the final receiver slot",
         "fn make()->i64{7} fn main(){let a={let x=make();x};print(a);}",
         "inferred", "7\n", 8),
        ("exclusive scalar sources share the receiver slot",
         "fn main(){let a=if false{let x:i64=7;x}else{let y:i64=8;y};print(a);}",
         "inferred", "8\n", 8),
        ("simultaneously live alternatives keep distinct slots",
         "fn main(){let a=loop{let x:i64=7;let y:i64=8;"
         "if true {break x;}else{break y;}};print(a);}",
         "inferred", "7\n", 16),
        ("pool storage", POOL, "inferred", "5\n", None),
        ("region-only annotation", "#(datastack: region_size=100M)\n" + CALL,
         "inferred", "7\n", None),
        ("unused recursion", RECURSION.split("fn main")[0] + CALL,
         "inferred", "7\n", None),
        ("explicit before inferred", "#(datastack: size=1K)\n" + CALL,
         "explicit", "7\n", 1024),
        ("explicit before default", "#(datastack: size=1K)\n" + RECURSION,
         "explicit", "3\n", 1024),
        ("recursive default", RECURSION, "default", "3\n", None),
        ("explicit exhausted", "#(datastack: size=1K)\n"
         "fn main(){let a:[i64;129]=[1;129];print(a[0]);}", "exhausted", "", None),
    ]
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        for name, source, policy, expected, fixed_bytes in cases:
            generated = emit(source)
            assert generated.returncode == 0, (name, generated.stderr)
            assert bool(re.search(r"^static size_t crust_bound_", generated.stdout, re.M)) == (
                policy == "inferred"
            ), name
            assert ("    crust_set_capacity(" in generated.stdout) == (policy != "default"), name
            for optimization in ("-O0", "-O2"):
                result = run_c(generated.stdout, directory, optimization)
                assert result.stdout == expected, (name, result)
                if policy == "exhausted":
                    assert result.returncode == 1 and result.stderr == (
                        "corbo: limite de la datastack fixe\n"
                    ), (name, result)
                    continue
                assert result.returncode == 0, (name, result)
                capacity, peak = map(int, result.stderr.strip().split(":"))
                assert 0 < peak <= capacity, (name, capacity, peak)
                if policy == "inferred":
                    assert capacity == peak, (name, capacity, peak)
                if fixed_bytes is not None:
                    assert capacity == fixed_bytes, (name, capacity)
            print(f"{name} OK")

    for annotation, diagnostic in [
        ("#(datastack: size=0K)", "positive"),
        ("#(datastack: size=0x10K)", "décimale"),
        ("#(datastack: size=1Ki)", "unité"),
        ("#(datastack: size=1K,size=2K)", "répétée"),
        ("#(datastack: size=18446744073709551615G)", "hors limites"),
    ]:
        result = emit(annotation + "\nfn main(){}")
        assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
    result = emit("fn main(){} #(datastack: size=1K)")
    assert result.returncode != 0 and "en tête" in result.stderr, result.stderr
    assert emit("#(datastack:) fn main(){}").returncode == 0
    print("6 refus d’annotation confirmés")


if __name__ == "__main__":
    main()
