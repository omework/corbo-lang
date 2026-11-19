#!/usr/bin/env python3
"""Check region-backed maps and vectors carrying lifetimes or owned slots."""

from check_rust_placement_dependencies import main, ACCEPTED, REJECTED

ACCEPTED[:] = [
    ("recursive synchronous entry replacement", """
        fn replace(entry:&mut &mut i64, next:&mut i64, n:i64){if n>0 {replace(entry,next,0);} else {*entry=next;}}
        fn relay(entry:&mut &mut i64, next:&mut i64){replace(entry,next,1);}
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{relay(v,&mut b);print(**v);},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n"),
    ("known keys release only the extracted loan", """
        fn main(){
            let mut a:i64=7;let mut b:i64=9;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();
            drop(m.insert(1,&mut a));drop(m.insert(2,&mut b));
            drop(m.remove(&k));a=11;print(a);
            let k:i64=2;match m.get(&k){Some(v)=>{print(**v);},None=>{}}
        }
    """, "11\n9\n"),
    ("entry replacement contract propagates through a relay", """
        fn replace(entry:&mut &mut i64, next:&mut i64){*entry=next;}
        fn relay(entry:&mut &mut i64, next:&mut i64){replace(entry,next);}
        fn main(){
            let mut a:i64=7;let mut b:i64=9;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
            match m.get_mut(&k){Some(v)=>{relay(v,&mut b);print(**v);},None=>{}}
            match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
            print(b);
        }
    """, "9\n11\n"),
    ("mutable map entry can replace its stored reference", """
        fn main(){
            let mut a:i64=7;let mut b:i64=9;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();
            drop(m.insert(1,&mut a));
            match m.get_mut(&k){Some(v)=>{*v=&mut b;print(**v);},None=>{}}
            match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
            drop(m);print(b);
        }
    """, "9\n11\n"),
    ("nested reference parameters preserve both access modes", """
        fn lire(v:&&mut i64)->i64{**v}
        fn ecrire(v:&mut &mut i64){**v=9;}
        fn main(){
            let mut n:i64=7;let mut vue=&mut n;
            print(lire(&vue));ecrire(&mut vue);print(n);
        }
    """, "7\n9\n"),
    ("map dependencies survive a function relay", """
        fn relay(m:HashMap<i64,&i64>)->HashMap<i64,&i64>{m}
        fn main(){
            let n:i64=7;let k:i64=1;
            let mut m=HashMap<i64,&i64>::new();
            drop(m.insert(1,&n));let m=relay(m);
            match m.get(&k){Some(v)=>{print(**v);},None=>{}}
        }
    """, "7\n"),
    ("map owned replacement and removal", """
        fn main(){
            let mut p=pool<i64>(2);
            let k:i64=1;
            let mut m=HashMap<i64,A<i64>>::new();
            drop(m.insert(1,p.new(7)));
            match m.insert(1,p.new(9)){Some(v)=>{print(*v);drop(v);},None=>{}}
            match m.get(&k){Some(v)=>{print(**v);},None=>{}}
            match m.remove(&k){Some(v)=>{print(*v);drop(v);},None=>{}}
            drop(m);let v=p.new(11);print(*v);
        }
    """, "7\n9\n9\n11\n"),
    ("map nested mutable borrow and extraction", """
        fn main(){
            let mut n:i64=7;
            let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();
            drop(m.insert(1,&mut n));
            match m.get(&k){Some(v)=>{print(**v);},None=>{}}
            match m.get_mut(&k){Some(v)=>{let w=&mut **v;*w=9;},None=>{}}
            match m.remove(&k){Some(v)=>{print(*v);},None=>{}}
            drop(m);print(n);
        }
    """, "7\n9\n9\n"),
    ("vector extraction returns slots to two source pools", """
        fn main(){
            let mut a=pool<i64>(1);let mut b=pool<i64>(1);
            let mut vp=pool<Vector<A<i64>>>(1);let mut v=vp.new();
            v.push(a.new(7));v.push(b.new(9));
            let first=v.remove(0);print(*first);drop(first);
            match v.pop(){Some(last)=>{print(*last);drop(last);},None=>{print(0);}}
            match v.pop(){Some(last)=>{drop(last);},None=>{print(1);}}
            let first=a.new(4);let last=b.new(5);print(*first);print(*last);
        }
    """, "7\n9\n1\n4\n5\n"),
    ("caller placement preserves path-specific pool cleanup", """
        struct Item{leaf:A<i64>}
        fn choose(p:&mut Pool<i64>,early:bool)->Item{
            let local=Item{leaf:p.new(1)};
            if early{return local;}
            Item{leaf:p.new(2)}
        }
        fn main(){
            let mut p=pool<i64>(2);
            let a=choose(&mut p,true);drop(a);print(1);
            let b=choose(&mut p,false);drop(b);print(2);
            let x=p.new(3);let y=p.new(4);print(*x);print(*y);
        }
    """, "1\n2\n3\n4\n"),
    ("map returned from an annotated child", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn make()->HashMap<i64,i64>{
            #(stack_region: max_size=2K,count=1) {
                let mut m=HashMap<i64,i64>::new();drop(m.insert(1,9));m
            }
        }
        fn main(){
            let mut a=make();let k:i64=1;
            match a.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
            match a.get_mut(&k){Some(v)=>{*v=11;},None=>{}}
            match a.remove(&k){Some(v)=>{print(v);},None=>{print(0);}}
            drop(a);
            let mut b=HashMap<i64,i64>::new();
            drop(b.insert(1,7));match b.get(&k){Some(v)=>{print(*v);},None=>{}}
        }
    """, "9\n11\n7\n"),
    ("consumed map releases its region in the callee", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn consume(m:HashMap<i64,i64>){let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{}}}
        fn main(){
            let mut a=HashMap<i64,i64>::new();drop(a.insert(1,4));consume(a);
            let mut b=HashMap<i64,i64>::new();drop(b.insert(1,5));consume(b);
        }
    """, "4\n5\n"),
    ("map forward and region bound", """
        fn relay(m:HashMap<u8,i64>)->HashMap<u8,i64>{m}
        fn main(){
            let mut m=HashMap<u8,i64>::new();drop(m.insert(2,8));let m=relay(m);
            let k:u8=2;match m.get(&k){Some(v)=>{print(*v);},None=>{}}
        }
    """, "8\n"),
    ("map entry address survives scope transfer, growth and reuse", """
        fn main(){
            let mut m=#(stack_region:max_size=2K,count=1){
                let mut m=HashMap<i64,i64>::new();
                drop(m.insert(1,42));
                let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
                m
            };
            let mut n:i64=2;
            while n<20 {drop(m.insert(copy(n),copy(n)));n=n+1;}
            let two:i64=2;drop(m.remove(&two));drop(m.insert(21,21));
            let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
        }
    """, "42\n42\n"),
    ("map collisions and hole reuse", """
        #(datastack: region_stack_size=1K,region_size=1K)
        fn main(){
            let mut m=HashMap<i64,i64>::new();let mut n:i64=0;
            while n<20 {drop(m.insert(copy(n),copy(n)));n=n+1;}
            let zero:i64=0;
            match m.insert(0,99){Some(v)=>{print(v);},None=>{}}
            match m.remove(&zero){Some(v)=>{print(v);},None=>{}}
            let mut round:i64=20;
            while round<100{
                drop(m.insert(copy(round),copy(round)));
                match m.remove(&round){Some(v)=>{},None=>{print(0);}}
                round=round+1;
            }
            let k:i64=19;match m.get(&k){Some(v)=>{print(*v);},None=>{}}
        }
    """, "0\n99\n19\n"),
    ("reference follows vector across calls", """
        fn relay(v:A<Vector<&i64>>)->A<Vector<&i64>>{v}
        fn main(){
            let mut n:i64=4;let mut p=pool<Vector<&i64>>(1);let mut v=p.new();
            v.push(&n);let v=relay(v);let r=v[0];print(*r);drop(v);n=9;print(n);
        }
    """, "4\n9\n"),
    ("mutable reference remains exclusive in vector", """
        fn main(){
            let mut n:i64=1;let mut p=pool<Vector<&mut i64>>(1);let mut v=p.new();
            v.push(&mut n);let r=&mut *v[0];*r=4;drop(v);print(n);
        }
    """, "4\n"),
    ("pool owns the active enum payload and releases its leaves", """
        struct Boxed{a:A<i64>}
        enum Entry{Empty,Live{payload:Boxed}}
        fn wrap(p:&mut Pool<Entry>, a:A<i64>)->A<Entry>{
            p.new(Entry.Live{payload:Boxed{a:a}})
        }
        fn main(){
            let mut leaves=pool<i64>(1);let mut entries=pool<Entry>(1);
            let e={wrap(&mut entries,leaves.new(7))};
            match &e{Entry.Live{payload:b}=>{print(*(*b).a);},Entry.Empty=>{print(0);}}
            drop(e);
            let e=wrap(&mut entries,leaves.new(9));
            match &e{Entry.Live{payload:b}=>{print(*(*b).a);},Entry.Empty=>{print(0);}}
        }
    """, "7\n9\n"),
    ("recursive type uses the same pool for its ownership tree", """
        enum Chain{End,Link{next:A<Chain>}}
        fn relay(head:A<Chain>)->A<Chain>{head}
        fn main(){
            let mut p=pool<Chain>(2);
            let tail=p.new(Chain.End);
            let middle=p.new(Chain.Link{next:tail});
            let head=p.new(Chain.Link{next:middle});
            drop(head);
            let tail=p.new(Chain.End);
            let middle=p.new(Chain.Link{next:tail});
            let head=p.new(Chain.Link{next:middle});
            let received=relay({head});
            drop(received);print(1);
        }
    """, "0:0\n1:0\n1:1\n0:0\n1:0\n1:1\n1\n"),
    ("pool struct vector and pool compose through scope cleanup", """
        struct Item{leaf:A<i64>,view:&i64}
        struct Root{items:A<Vector<Item>>}
        fn main(){
            let source:i64=8;
            let mut leaves=pool<i64>(1);let mut vectors=pool<Vector<Item>>(1);
            let mut roots=pool<Root>(1);
            {
                let mut v=vectors.new();
                {let a=leaves.new(7);v.push(Item{leaf:a,view:&source});}
                let r=v[0].view;print(*v[0].leaf);print(*r);
                let root=roots.new(Root{items:v});
            }
            let mut v=vectors.new();
            v.push(Item{leaf:leaves.new(9),view:&source});
            let root=roots.new(Root{items:v});drop(root);
            print(source);let a=leaves.new(10);print(*a);
        }
    """, "7\n8\n8\n10\n"),
    ("owned slots follow the vector", """
        fn consume(v:A<Vector<A<i64>>>){print(*v[0]);print(*v[1]);}
        fn main(){
            let mut a=pool<i64>(1);let mut b=pool<i64>(1);let mut vp=pool<Vector<A<i64>>>(1);
            let mut v=vp.new();
            {let x=a.new(7);v.push(x);let y=b.new(8);v.push(y);}
            consume(v);
            let x=a.new(9);let y=b.new(10);print(*x);print(*y);
        }
    """, "7\n8\n9\n10\n"),
]

REJECTED[:] = [
    ("entry replacement contract rejects a shorter target", """
        fn replace(entry:&mut &mut i64, next:&mut i64){*entry=next;}
        fn main(){
            let mut a:i64=7;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
            {let mut b:i64=9;match m.get_mut(&k){Some(v)=>{replace(v,&mut b);},None=>{}}}
            drop(m);
        }
    """, "survivrait"),
    ("other key still carries its loan after removal", """
        fn main(){
            let mut a:i64=7;let mut b:i64=9;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();
            drop(m.insert(1,&mut a));drop(m.insert(2,&mut b));
            drop(m.remove(&k));b=11;
            let k:i64=2;match m.get(&k){Some(v)=>{print(**v);},None=>{}}
        }
    """, "emprunt actif"),
    ("replacing a map entry cannot install a shorter borrow", """
        fn main(){
            let mut a:i64=7;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();
            drop(m.insert(1,&mut a));
            {let mut b:i64=9;match m.get_mut(&k){Some(v)=>{*v=&mut b;},None=>{}}}
            drop(m);
        }
    """, "survivrait"),
    ("shared entry loan cannot write through a mutable reference", """
        fn main(){
            let mut n:i64=7;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();
            drop(m.insert(1,&mut n));
            match m.get(&k){Some(v)=>{**v=9;},None=>{}}
        }
    """, "écriture par une référence partagée"),
    ("map entry cannot outlive its borrowed target", """
        fn main(){
            let mut m=HashMap<i64,&i64>::new();
            {let n:i64=7;drop(m.insert(1,&n));}
        }
    """, "survivrait"),
    ("owned map keeps its source pool alive", """
        fn main(){
            let mut p=pool<i64>(1);
            let mut m=HashMap<i64,A<i64>>::new();
            drop(m.insert(1,p.new(7)));drop(p);
        }
    """, "encore une allocation"),

    ("nested vector owner cannot outlive the leaf pool", """
        struct Item{leaf:A<i64>}
        fn main(){
            let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();
            {let mut inner=pool<i64>(1);v.push(Item{leaf:inner.new(1)});}
            drop(v);
        }
    """, "survivrait"),
    ("nested pooled aggregate keeps both source pools live", """
        struct Item{leaf:A<i64>}
        fn main(){
            let mut leaves=pool<i64>(1);let mut items=pool<Item>(1);
            let a=items.new(Item{leaf:leaves.new(1)});drop(leaves);drop(a);
        }
    """, "encore une allocation"),
    ("nested owner cannot escape from a shorter pool", """
        struct Item{leaf:A<i64>}
        fn main(){
            let mut items=pool<Item>(1);
            let a={let mut leaves=pool<i64>(1);items.new(Item{leaf:leaves.new(1)})};
            drop(a);
        }
    """, "sortie du bloc"),
    ("map entry loan protects mutation", """
        fn main(){
            let mut m=HashMap<i64,i64>::new();drop(m.insert(1,2));let k:i64=1;
            let r=m.get(&k);drop(m.remove(&k));
            match r{Some(v)=>{print(*v);},None=>{}}
        }
    """, "emprunt actif"),
    ("vector rejects a shorter reference", """
        fn main(){
            let mut p=pool<Vector<&i64>>(1);let mut v=p.new();
            {let n:i64=1;v.push(&n);}
        }
    """, "survivrait"),
    ("branch carries source pool dependency", """
        fn main(){
            let mut p=pool<i64>(1);let mut vp=pool<Vector<A<i64>>>(1);let mut v=vp.new();
            if true {let a=p.new(3);v.push(a);}
            drop(p);drop(v);
        }
    """, "encore une allocation"),
    ("loop carries stored reference dependency", """
        fn main(){
            let mut x:i64=1;let mut p=pool<Vector<&i64>>(1);let mut v=p.new();let mut n:i64=0;
            while n<2 {v.push(&x);n=n+1;}
            x=3;let r=v[0];print(*r);
        }
    """, "emprunt actif"),
]

def instrument_storage(name, generated):
    if name == "map entry address survives scope transfer, growth and reuse":
        anchor = "    return slot == 0 ? NULL : crust_region_data(&map->contents)"
        assert generated.count(anchor) == 1
        return generated.replace(anchor, """
    static const void *original_entry;
    if (key == 1 && slot != 0) {
        const void *entry = crust_region_data(&map->contents)
            + slot + crust_map_round(sizeof(CrustMapEntry));
        if (original_entry == NULL)
            original_entry = entry;
        else if (original_entry != entry)
            abort();
    }
""" + anchor)

    if name != "recursive type uses the same pool for its ownership tree":
        return generated
    release = "        allocation->arm = NULL;"
    assert generated.count(release) == 1
    return generated.replace(release,
        '        printf("%zu:%zu\\n", allocation->tag, allocation->index);\n' + release)


if __name__ == "__main__":
    main(instrument_storage)
