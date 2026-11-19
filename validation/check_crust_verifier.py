"""Compare verifier outcomes on the validated program corpus."""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import subprocess
import tempfile

from check_crust_bootstrap import FRONTEND, PACKAGE
from check_crust_parser import corpus
from check_crust_static_tree import REGRESSIONS as STATIC_REGRESSIONS


DEFERRED_ENTRY = (
    "async fn replace(e:&mut &mut i64,n:&mut i64){yield;*e=n;} "
    "async fn root(){let mut a=7;let mut b=9;let k=1;"
    "let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));"
    "match m.get_mut(&k){Some(v)=>{let h=runtime::spawn_blocking(replace(v,&mut b));"
    "%s},None=>{}}} fn main(){let h=runtime::spawn(root());drop(h.join());}"
)

REGRESSIONS = (
    # A later projection of the same field keeps its root reserved.
    ("""
struct V { a:&i64, b:&i64 }
fn main() {
    let mut x:i64=1; let y:i64=2;
    let v=V{a:&x,b:&y}; let r=v.a; print(*r);
    x=3; let s=v.a; print(*s);print(x);
}
""", 8),
    # Discard nested result.
    ("""
enum Envelope{Waiting{h:runtime::Handle<Void>}}
fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
 let h=runtime::thread({move entry;move next;*entry=next;});
 Envelope.Waiting{h:h}
}
fn main(){
 let mut a:i64=7;let mut b:i64=9;let k:i64=1;
 let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
 match m.get_mut(&k){
   Some(v)=>{let next=&mut b; let outer=runtime::thread({move v;move next;start(v,next)}); drop(outer.join());},
   None=>{}
 }
 match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
 print(b);
}
""", 8),
    # Discard conditional envelope.
    ("""
fn start(entry:&mut &mut i64,next:&mut i64)->runtime::Handle<Void>{runtime::thread({move entry;move next;*entry=next;})}
enum Envelope { Empty, Waiting{h:runtime::Handle<Void>} }
fn relay(h:runtime::Handle<Void>, n:i64, wait:bool)->Envelope {
    if n>0 {relay(h,n-1,wait)} else {
        if wait {drop(h.join());Envelope.Empty} else {Envelope.Waiting{h:h}}
    }
}
fn main(){
 let mut a:i64=7;let mut b:i64=9;let k:i64=1;
 let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
 match m.get_mut(&k){
  Some(v)=>{let h=start(v,&mut b);
   let mut pool=pool<Vector<runtime::Handle<Void>>>(1);let mut vhandles=pool.new();vhandles.push(h);let h=vhandles.remove(0);let e=relay(h,2,false);
   drop(e);
   print(**v);
  },None=>{}
 }
 match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
 print(b);
}
""", 8),
    # Write alternate loan root.
    ("""
struct View{r:&i64}
async fn root(take_left:bool)->i64 {
    let a:i64=10;let mut b:i64=20;
    let task=if take_left {leaf(&a)} else {leaf(&b)};
    let view=task.await;
    b=29;let r=view.r;*r
}
async fn leaf(r:&i64)->View {yield;View{r:r}}
fn main(){
    let a=runtime::spawn(root(true));let b=runtime::spawn(root(false));
    match a.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
    match b.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
}
""", 8),
    (DEFERRED_ENTRY % "drop(h.await);print(**v);", 0),
    (DEFERRED_ENTRY % "print(**v);drop(h.await);", 8),
    ('struct Bad { field: Missing } fn main() {}', 8),
    ('struct ANode { next: BNode } struct BNode { next: ANode } fn main() {}', 8),
    ('struct Node { next: A<Node> } fn main() {}', 0),
    ('fn main(){ let p = pool<i64>(0x0); }', 8),
    ('fn helper() {}', 8),
    ('#(datastack: size=18446744073709551615G) fn main() {}', 8),
    ('fn main() { #(stack_region: max_size=18446744073709551615G) {} }', 8),
    ('async fn main() {}', 8),
    ('struct Item {} impl Item { fn drop(&self) {} } fn main() {}', 8),
    ('struct Item {} impl Item { fn drop(&mut self) {} fn drop(&mut self) {} } fn main() {}', 8),
    ('fn increment(n: &mut i64) { *n = *n + 1; } '
     'fn main() { let mut n = 41; increment(&mut n); print(n); }', 0),
    ('fn increment(n: &mut i64) { *n = *n + 1; } '
     'fn main() { let n = 41; increment(&mut n); }', 8),
    ('fn main() { let n: u8 = 4; let m = n + 1; print(n); print(m); }', 0),
    ('fn main() { let n = 4; print(n / 0); }', 8),
    ('fn main() { let n = 4; print(n / -0); }', 8),
    ('fn main() { let n = 4; let r = &n; print(copy(*r)); }', 8),
    ('struct Bad { n: Vector } fn main() {}', 8),
    ('fn main() { let a = {{ let x: i64 = 7; let y = x; y }}; print(a); }', 0),
    ('fn main() { let x = 1; let n = {x}; print(x); }', 8),
    ('fn f(n: i64) -> i64 { if n == 0 { 0 } else { let k = n - 1; f(k) + 1 } } '
     'fn main() { print(f(3)); }', 0),
    ('fn main() { let n:u8=4; let mut row=[1,n]; row[1]=7; print(row[0]); }', 0),
    ('fn main() { let mut row:[u8;2]=[0;2]; let mut r=&mut row[1]; '
     '*r=7; print(row[1]); }', 0),
    ('fn main() { let mut row=[1,2]; let r=&row[0]; row[0]=7; print(*r); }', 8),
    ('fn main() { let row:[u8;2]=[0;2]; print(row[1+1]); }', 8),
    ('struct Inner{x:i64} struct Outer{inner:Inner, bytes:[u8;2]} '
     'fn main(){let b:Outer=Outer{inner:Inner{x:7},bytes:[0;2]}; '
     'print(b.inner.x); print(b.bytes[1]);}', 0),
    ('fn main() { let row=[1,2]; let moved=row; print(row[0]); }', 8),
    ('fn main() { let row:[u8;2]=[0;1]; }', 8),
    ('fn main() { let x=loop {let n:u8=7;if false {break n;}break 1;}; print(x); }', 0),
    ('fn main() { let x:u8=loop {break 256;}; print(x); }', 8),
    ('async fn f()->i64{1} async fn g(){f().await;} fn main(){}', 8),
    ('async fn count(n:i64)->i64{yield;n+1} fn main(){'
     'let f=count(6);let h=runtime::spawn(f);'
     'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}}', 0),
    ('fn main(){let n:i64=6;let h=runtime::thread({move n;n+1});'
     'match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}}', 0),
    ('fn main(){let n:i64=6;let h=runtime::thread({print(n);});drop(h.join());}', 8),
    ('fn main(){let mut a=[[1,2],[3,4]];let r=&mut a[1][0];*r=7;print(a[1][0]);}', 0),
    ('fn main(){let mut a=[[1,2],[3,4]];let r=&mut a[0][0];'
     'let s=&mut a[1][0];print(*r);print(*s);}', 8),
    ('fn main(){let f:f32=.5;print(1.+f);}', 0),
    ('fn main(){let f:f64=1.;print(f as f32);}', 8),
    ('fn make(p:&mut Pool<i64>)->A<i64>{p.new(5)} fn main(){'
     'let mut p=pool<i64>(1);let a=make(&mut p);drop(p);print(*a);}', 8),
    ('fn main(){let mut a=[1,2];let r=&a[0];a[0]=*r;print(a[0]);}', 0),
    ('fn main(){let mut a=[1,2];let r=&a[0];a[0]=*r;print(*r);}', 8),
    ('fn main(){let mut a=[1,2];let r=&mut a[0];a[0]=*r;print(a[0]);}', 8),
    ('fn choose(a:&[i64;2])->i64{(*a)[1]} fn main(){let a=[1,2];print(choose(&a));}', 0),
    ('fn main(){let a=[1,2];let r=&a;drop(a);print((*r)[0]);}', 8),
    ('enum E{Empty,Full{n:i64}} fn main(){let mut p=pool<E>(2);let a=p.new(E.Full{n:9});'
     'match &a{E.Empty=>{},E.Full{n:n}=>{print(n);}}drop(a);}', 0),
    ('async fn first(row:[i64;2])->i64{yield;row[0]} '
     'fn main(){let row=[7,8];let h=runtime::spawn(first(row));drop(h);}', 0),
    ('fn main(){let mut m=HashMap<i64,i64>::new();let k=1;drop(m.insert(1,2));'
     'match m.get_mut(&k){Some(v)=>{*v=4;},None=>{}}drop(m);}', 0),
    ('fn main(){let mut m=HashMap<i64,i64>::new();let k=1;drop(m.insert(1,2));'
     'let r=m.get(&k);drop(m.remove(&k));match r{Some(v)=>{print(*v);},None=>{}}}', 8),
    ('fn main(){let mut x=1;let mut y=2;let mut a=[&mut x,&mut y];'
     'let v=&mut a;let r=&mut *(*v)[0];let s=&mut *(*v)[1];*r=3;*s=4;print(x);print(y);}', 0),
    ('fn main(){let mut x=1;let mut a=[&mut x];let v=&mut a;'
     'let r=&mut *(*v)[0];drop(v);*r=3;}', 8),
    ('fn main(){let mut p=pool<i64>(1);let mut m=HashMap<i64,A<i64>>::new();'
     'drop(m.insert(1,p.new(7)));drop(p);}', 8),
    ('fn main(){let mut p=pool<i64>(1);let mut m=HashMap<i64,A<i64>>::new();'
     'let key=1;drop(m.insert(1,p.new(7)));drop(m.remove(&key));drop(p);}', 0),
    ('async fn update(n:&mut i64){yield;*n=2;} fn main(){let mut n=0;'
     'let f=update(&mut n);let h=runtime::spawn(f);drop(h.join());print(n);}', 0),
    ('async fn update(n:&mut i64){yield;*n=2;} fn main(){let mut n=0;'
     'let f=update(&mut n);let h=runtime::spawn(f);print(n);drop(h.join());}', 8),
    ('fn start(r:&mut i64)->runtime::Handle<()>{runtime::thread({move r;*r=1;})}'
     'fn main(){let mut n=0;let h=start(&mut n);drop(h.join());print(n);}', 0),
    ('fn start(r:&mut i64)->runtime::Handle<()>{runtime::thread({move r;*r=1;})}'
     'fn main(){let mut n=0;let h=start(&mut n);print(n);drop(h.join());}', 8),
    ('async fn update(n:&mut i64){yield;*n=2;} fn main(){let mut n=0;let r=&mut n;'
     'let f=update(r);let h=runtime::spawn(f);*r=7;drop(h.join());}', 8),
    ('struct View{left:&mut i64,right:&mut i64} fn main(){let mut n=1;'
     'let mut v=View{left:&mut n,right:&mut n};let r=&mut *v.right;*r=2;}', 8),
    ('fn main(){let mut a=7;let mut b=9;let k=1;let mut m=HashMap<i64,&mut i64>::new();'
     'drop(m.insert(1,&mut a));match m.get_mut(&k){Some(v)=>{*v=&mut b;},None=>{}}'
     'a=3;match m.get(&k){Some(v)=>{print(**v);},None=>{}}}', 8),
    ('fn main(){let mut a=[1];let v=&mut a[..];print(v.len());print(a[0]);}', 0),
    ('fn main(){let mut a=[1];let v=&mut a[..];print(a[0]);print(v.len());}', 8),
    ('fn main(){let x=(1,2);let y=x;let (a,b)=y;print(a);print(b);}', 0),
    ('fn main(){let x=(1,2);let y=x;let (a,b)=y;drop(y);}', 8),
    ('fn main(){let mut p=pool<i64>(1);let mut vp=pool<Vector<A<i64>>>(1);let mut v=vp.new();'
     'if true{let a=p.new(3);v.push(a);}drop(v);drop(p);}', 0),
    ('fn main(){let mut x=1;let mut p=pool<Vector<&i64>>(1);let mut v=p.new();let mut n=0;'
     'while n<2{v.push(&x);n=n+1;}drop(v);x=3;print(x);}', 0),
    ('fn reorder(a:[&i64;2], b:bool)->[&i64;2]{if b{[a[1],a[0]]}else{reorder(a,true)}}'
     'fn main(){let x=1;let y=2;let a=reorder([&x,&y],false);let r=a[0];print(*r);}', 0),
    ('fn main(){ @unchecked { @asm { nop } } }', 0),
)
LABELS = {0: "accepted", 8: "rule violation", 9: "unsupported"}

ADDRESS_DETAIL = b"corboc: addr requires a reference argument\n"
RECEIVER_DETAIL = b"corboc: this type of by-value self receiver is not supported\n"
UNKNOWN_DETAIL = b"corboc: unknown qualified function: "


def check_diagnostics(bootstrap, work):
    path = work / "diagnostic.crb"
    cases = (
        ("fn main(){@unchecked {let p=addr(12);drop(p);}}", 8, 1, "12", ADDRESS_DETAIL),
        ("fn main(){print(leaf::value());}", 8, 8, "leaf", UNKNOWN_DETAIL + b"leaf::value\n"),
        ("struct Packet { bytes:&u8 } "
         "impl Packet { fn read(self:Packet)->u8 { *self.bytes } } fn main(){}", 9, None, None,
         RECEIVER_DETAIL),
    )
    human_details = (platform.system(), platform.machine()) == ("Darwin", "arm64")
    for source, status, rule, token, detail in cases:
        path.write_text(source)
        expected = b"" if rule is None else f"{rule}\n{source.index(token)}\n".encode()
        for mode in ("--verify", "--emit-c"):
            actual = subprocess.run([bootstrap, mode, path], capture_output=True, timeout=15)
            assert (actual.returncode, actual.stdout, actual.stderr) == (
                status, expected, detail if human_details else b"",
            ), (source, actual)
    print("Three precise diagnostics matched in --verify and --emit-c")


def rust_batch(mode, sources):
    requests = "".join(f"{mode}\t{source.encode().hex()}\n" for source in sources)
    result = subprocess.run([FRONTEND, "--batch"], input=requests, text=True,
                            capture_output=True, check=True)
    assert not result.stderr, result.stderr
    return result.stdout.splitlines()


def compare(bootstrap, work, report):
    cases = {}
    for label, source in corpus():
        if len(source.encode()) <= 131072:
            cases.setdefault(source, label)
    for index, source in enumerate(STATIC_REGRESSIONS):
        cases.setdefault(source, f"static fixture {index}")
    for index, (source, _) in enumerate(REGRESSIONS):
        cases.setdefault(source, f"verifier fixture {index}")
    parsed = [source for source, row in zip(cases, rust_batch("ast", cases), strict=True)
              if row.split("\t", 1)[0] == "OK"]
    assert all(source in parsed for source, _ in REGRESSIONS)
    expected_status = dict(REGRESSIONS)
    path = work / "input.crb"
    counts = Counter()
    mismatches = []
    for source, reference in zip(parsed, rust_batch("verify", parsed), strict=True):
        path.write_text(source)
        result = subprocess.run([bootstrap, "--verify", path], text=True, capture_output=True, timeout=15)
        status = result.returncode
        label = cases[source]
        detail = result.stderr.encode()
        assert status in LABELS and (
            not detail or (status == 9 and detail == RECEIVER_DETAIL)
            or (status == 8 and (detail == ADDRESS_DETAIL or detail.startswith(UNKNOWN_DETAIL)))
        ), (label, result)
        if status == 8:
            rule, byte = map(int, result.stdout.splitlines())
            assert 1 <= rule <= 8 and 0 <= byte <= len(source.encode()), (label, result)
        else:
            assert not result.stdout, (label, result)
        rust_ok = reference == "OK"
        counts[rust_ok, status] += 1
        if source in expected_status:
            assert status == expected_status[source], (label, source, result)
            assert rust_ok == (status == 0), (label, source, reference)
        if status == 9 or rust_ok != (status == 0):
            mismatches.append(dict(label=label, rust=reference, crust=LABELS[status],
                                   diagnostic=result.stderr.strip() or result.stdout.strip(), source=source))
    if report:
        report.write_text("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in mismatches))
    print(f"{len(parsed)} validated program ASTs")
    print(f"{counts[True, 0]} both accept, {counts[False, 8]} both issue a rejection")
    print(f"{counts[False, 0]} Crust false accepts, {counts[True, 8]} Crust false rejections")
    print(f"{counts[True, 9]} unsupported with Rust acceptance, "
          f"{counts[False, 9]} unsupported with Rust rejection")
    assert not counts[False, 0], "Crust accepted a program Rust rejected"
    assert not counts[True, 8], "Crust rejected a program Rust accepted"
    return not (counts[True, 9] or counts[False, 9])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--bootstrap", type=Path, help="run an existing bootstrap executable")
    cli.add_argument("--report", type=Path, help="write mismatches as JSON lines")
    cli.add_argument("--require-parity", action="store_true", help="also fail if Crust reports unsupported")
    options = cli.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        bootstrap = options.bootstrap
        if bootstrap is None:
            generated = work / "bootstrap.c"
            bootstrap = work / "bootstrap"
            with generated.open("w") as output:
                subprocess.run([FRONTEND, "emit-c", PACKAGE], stdout=output, check=True)
            subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                            "-fno-sanitize-recover=all", generated, "-o", bootstrap], check=True)
        check_diagnostics(bootstrap.resolve(), work)
        parity = compare(bootstrap.resolve(), work, options.report)
        if options.require_parity and not parity:
            raise SystemExit("Verifier parity is incomplete")


if __name__ == "__main__":
    main()
