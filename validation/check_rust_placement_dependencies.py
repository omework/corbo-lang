#!/usr/bin/env python3
"""Exercise fixed placement across borrowed aggregates and local pool owners."""

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

ACCEPTED = [('whole', 'fn get(a:&[i64;2])->i64 {(*a)[1]} fn main(){let a=[1,2];print(get(&a));}', '2\n'),
 ('field',
  'struct P {n:i64} fn field(p:&mut P)->&mut i64 {&mut (*p).n} fn main(){let mut p=P{n:3};let '
  'r=field(&mut p);*r=9;print(p.n);}',
  '9\n'),
 ('row', 'fn main(){let mut a=[[1,2],[3,4]];let mut r=&mut a[1][0];*r=7;print(a[1][0]);}', '7\n'),
 ('refs',
  'struct View{n:&i64} fn wrap(x:&i64)->View {View{n:x}} fn main(){let n:i64=17;let '
  'v={wrap(&n)};let r=v.n;print(*r);}',
  '17\n'),
 ('refs_array',
  'fn main(){let a:i64=1;let b:i64=2;let refs=[&a,&b];let i:u64=1;let r=refs[i];print(*r);}',
  '2\n'),
 ('pool_enum',
  'enum E{Empty,Data{n:u64}} fn main(){let mut p=pool<E>(1);let a=p.new(E.Empty);let '
  'b=p.new(E.Data{n:9});match &b{E.Empty=>{print(0);},E.Data{n:v}=>{print(v);}} drop(a);drop(b);}',
  '9\n'),
 ('pool_arg',
  'fn take(p:&mut Pool<i64>)->A<i64>{p.new(42)} fn relay(p:&mut Pool<i64>)->A<i64>{take(p)} fn '
  'consume(x:A<i64>){print(*x);} fn main(){let mut p=pool<i64>(1);let a=relay(&mut '
  'p);consume(a);let b=relay(&mut p);consume(b);}',
  '42\n42\n'),
 ('pool_scope',
  'fn main(){let mut p=pool<i64>(1);let a={let b=p.new(5);b};print(*a);{move a;print(*a);}let '
  'c=p.new(9);print(*c);}',
  '5\n5\n9\n'),
 ('pool_choice',
  'fn make(p:&mut Pool<i64>,q:&mut Pool<i64>,b:bool)->A<i64>{if b {p.new(1)}else{q.new(2)}} fn '
  'main(){let mut p=pool<i64>(1);let mut q=pool<i64>(1);let a=make(&mut p,&mut '
  'q,false);print(*a);drop(a);let b=make(&mut p,&mut q,true);print(*b);}',
  '2\n1\n'),
 ('pool_pass_enum',
  'enum E{Small{n:i64},Empty} fn take(p:&mut Pool<E>)->A<E>{p.new(E.Small{n:5})} fn main(){let mut '
  'p=pool<E>(1);let a=take(&mut p);match &a {E.Small{n:n}=>{print(n);},E.Empty=>{print(0);}}}',
  '5\n'),
 ('stored_mut',
  'struct V{r:&mut i64} fn wrap(x:&mut i64)->V {V{r:x}} fn main(){let mut n:i64=3;let mut '
  'v=wrap(&mut n);let mut q=&mut *v.r;*q=7;print(n);}',
  '7\n'),
 ('stored_mut_array',
  'fn main(){let mut n:i64=3;let mut a=[&mut n];let mut r=&mut *a[0];*r=6;print(n);}',
  '6\n'),
 ('pool_loop',
  'fn make(p:&mut Pool<i64>)->A<i64>{p.new(3)} fn main(){let mut p=pool<i64>(1);let a=loop {let '
  'b=make(&mut p);break b;};print(*a);drop(a);let c=p.new(9);print(*c);}',
  '3\n9\n'),
 ('pool_with_refs',
  'struct V{r:&i64} fn make(p:&mut Pool<V>, n:&i64)->A<V>{p.new(V{r:n})} fn main(){let '
  'n:i64=10;let mut p=pool<V>(1);let a={make(&mut p,&n)};let r=(*a).r;print(*r);drop(a);}',
  '10\n')]

REJECTED = [('local_view', 'struct V{r:&i64} fn bad()->V{let a:i64=1;V{r:&a}} fn main(){}', 'cible locale'),
 ('owned_field', 'struct V{r:&i64,n:i64} fn bad(a:V)->&i64{&a.n} fn main(){}', 'cible locale'),
 ('branch_view',
  'struct V{r:&i64} fn main(){let n:i64=1;let v=if true{V{r:&n}}else{let '
  'k:i64=2;V{r:&k}};drop(v);}',
  'sortie du bloc'),
 ('row_conflict',
  'fn main(){let mut a=[[1,2],[3,4]];let x=&mut a[0][0];let y=&mut a[1][0];print(*x);print(*y);}',
  'emprunt actif'),
 ('write_with_borrow', 'fn main(){let mut a=[1,2];let r=&a[0];a[0]=3;print(*r);}', 'emprunt actif'),
 ('stored_mut_extraction',
  'fn main(){let mut n:i64=1;let a=[&mut n];let r=a[0];print(*r);}',
  'réemprunt explicite'),
 ('local_pool', 'fn bad()->A<i64>{let mut p=pool<i64>(1);p.new(4)} fn main(){}', 'cible locale'),
 ('block_pool', 'fn main(){let a={let mut p=pool<i64>(1);p.new(4)};print(*a);}', 'sortie du bloc'),
 ('pool_drop',
  'fn make(p:&mut Pool<i64>)->A<i64>{p.new(5)} fn main(){let mut p=pool<i64>(1);let a=make(&mut '
  'p);drop(p);print(*a);}',
  'encore une allocation'),
 ('pool_content_escape',
  'struct V{r:&i64} fn make(p:&mut Pool<V>)->A<V>{let a:i64=1;p.new(V{r:&a})} fn main(){}',
  'cible locale')]


ACCEPTED += [
    ('field origins', """
        struct V { a:&i64, b:&i64 }
        fn left(v:V)->&i64 { v.a }
        fn main() {
            let x:i64=1; let mut y:i64=2;
            let v=V{a:&x,b:&y}; let r=left(v); y=3;
            print(*r);print(y);
        }""",'1\n3\n'),
    ('array origins', """
        fn select(a:[&i64;2])->&i64 { a[0] }
        fn main() {
            let x:i64=1; let mut y:i64=2;
            let a=[&x,&y]; let r=select(a); y=3; print(*r);print(y);
        }""",'1\n3\n'),
    ('last field use', """
        struct V { a:&i64, b:&i64 }
        fn main() {
            let mut x:i64=1; let y:i64=2;
            let v=V{a:&x,b:&y}; let r=v.a; print(*r);
            x=3; let s=v.b; print(*s);print(x);
        }""",'1\n2\n3\n'),
    ('stored distinct through borrowed aggregate', """
        fn main() {
            let mut x:i64=1; let mut y:i64=2;
            let mut a=[&mut x,&mut y]; let p=&mut a;
            let r=&mut *(*p)[0]; let s=&mut *(*p)[1];
            *r=7; *s=8; print(x);print(y);
        }""",'7\n8\n'),
    ('match borrowed fixed array', """
        enum E{Data{a:[i64;2]},Empty}
        fn main(){
            let mut e=E.Data{a:[1,2]};
            match &mut e {E.Data{a:row}=>{let r=&mut (*row)[1];*r=9;},E.Empty=>{}}
            match &e{E.Data{a:row}=>{print((*row)[1]);},E.Empty=>{print(0);}}
        }""",'9\n'),
    ('match borrowed pool struct', """
        struct S{n:i64}
        enum E{Data{s:S},Empty}
        fn main(){
            let mut p=pool<E>(1);let a=p.new(E.Data{s:S{n:8}});
            match &a {E.Data{s:view}=>{print((*view).n);},E.Empty=>{print(0);}}
            drop(a);
        }""",'8\n'),
    ('disjoint projected read', """
        struct V{left:&mut i64,right:&i64}
        fn main(){
            let mut n:i64=1;let m:i64=2;
            let mut v=V{left:&mut n,right:&m};let p=&mut v;
            let r=&mut *(*p).left;let s=(*p).right;
            *r=4;print(*s);print(n);
        }""", '2\n4\n'),
    ('reordered result positions', """
        fn swap(a:[&i64;2])->[&i64;2] { [a[1],a[0]] }
        fn main(){
            let mut n:i64=1;let m:i64=2;let a=swap([&n,&m]);
            let r=a[0];n=4;print(*r);print(n);
        }""", '2\n4\n'),

]

REJECTED += [
    ('dynamic index overlaps', """
        fn main() {
            let mut x:i64=1; let mut y:i64=2;
            let mut a=[&mut x,&mut y]; let p=&mut a;let i:i64=0;
            let r=&mut *(*p)[i];let s=&mut *(*p)[1];*r=7;*s=8;
        }""", 'emprunt actif'),
    ('shared aggregate', """
        fn main() {
            let mut n:i64=1;let a=[&mut n];let p=&a;let r=&mut *(*p)[0];*r=8;
        }""", 'agrégat partagé'),
    ('pool variant field survives', """
        struct S{n:i64} enum E{Data{s:S},Empty}
        fn main(){
            let mut p=pool<E>(1);let a=p.new(E.Data{s:S{n:8}});
            match &a {E.Data{s:view}=>{drop(a);print((*view).n);},E.Empty=>{}}
        }""", 'emprunt actif'),
    ('dynamic provenance through call', """
        fn select(a:[&i64;2], i:i64)->&i64 { a[i] }
        fn main() {
            let x:i64=1; let mut y:i64=2;
            let a=[&x,&y]; let r=select(a,0); y=3; print(*r);
        }""", 'emprunt actif'),
    ('recursive origins are conservative', """
        fn swap(a:[&i64;2], b:bool)->[&i64;2] {
            if b {[a[1],a[0]]} else {swap(a,true)}
        }
        fn main(){
            let x:i64=1;let mut y:i64=2;
            let a=swap([&x,&y],false);let r=a[0];y=4;print(*r);
        }""", 'emprunt actif'),
    ('parent unavailable during stored reborrow', """
        fn main(){
            let mut n:i64=1;let mut a=[&mut n];let p=&mut a;
            let r=&mut *(*p)[0];drop(p);*r=4;
        }""", 'réemprunt actif'),

]

def compile_crust(source):
    return subprocess.run(
        [FRONTEND, "emit-c"], input=source, text=True, capture_output=True
    )


def main(instrument=None):
    for name, source, diagnostic in REJECTED:
        result = compile_crust(source)
        assert result.returncode != 0 and diagnostic in result.stderr, (name, result.stderr)
    print(f"{len(REJECTED)} refus confirmés")

    with tempfile.TemporaryDirectory() as directory:
        source_path = Path(directory) / "witness.c"
        binary = Path(directory) / "witness"
        for name, source, expected in ACCEPTED:
            result = compile_crust(source)
            assert result.returncode == 0, (name, result.stderr)
            generated = result.stdout if instrument is None else instrument(name, result.stdout)
            source_path.write_text(generated)
            for optimization in ("-O0", "-O2"):
                subprocess.run(
                    [
                        "cc", "-std=c11", optimization, "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        source_path, "-lm", "-o", binary,
                    ],
                    check=True,
                )
                output = subprocess.check_output([binary], text=True)
                assert output == expected, (name, optimization, output)
            print(f"{name} OK")


if __name__ == "__main__":
    main()
