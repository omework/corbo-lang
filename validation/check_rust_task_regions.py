#!/usr/bin/env python3
"""Check handles, dependent captures and pollable async frames."""

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

ASYNC_METHOD = """
        struct Source { value: u8 }
        impl Source {
            async fn read(&mut self, buffer: &mut [u8]) -> usize {
                yield;
                buffer[0] = (*self).value;
                1
            }
        }
        async fn run() -> usize {
            let mut source = Source { value: 42 };
            let mut buffer: [u8; 1] = [0];
            let reading = source.read(&mut buffer[..]);
            let count = reading.await;
            print(buffer[0]);
            drop(source);
            count
        }
        fn main() {
            let execution = runtime::spawn(run());
            match execution.join() {
                Ok(count) => { print(count); },
                Err(_) => { print(0); },
            }
        }
    """

ACCEPTED = [
    ("async method retains the receiver and destination slice across suspension",
     ASYNC_METHOD, "42\n1\n", False),
    ("a dynamic index identifies the only handle", """
        fn run(index:i64) {
            let mut nombre:i64=7;
            let vue=&mut nombre;
            let mut pool=pool<Vector<runtime::Handle<Void>>>(1);
            let mut handles=pool.new();
            handles.push(runtime::thread({move vue;*vue=9;}));
            let h=handles.remove(index);
            drop(h.join());
            print(nombre);
        }
        fn main(){run(0);}
    """, "9\n", False),
    ("pop until None clears dependent handles even with unknown length", """
        fn run(second:bool) {
            let mut nombre:i64=7;
            let vue=&mut nombre;
            let mut pool=pool<Vector<runtime::Handle<Void>>>(1);
            let mut handles=pool.new();
            handles.push(runtime::thread({move vue;*vue=9;}));
            if second { handles.push(runtime::thread({})); }
            loop {
                match handles.pop() {
                    Some(h)=>{drop(h.join());},
                    None=>{break;}
                }
            }
            print(nombre);
        }
        fn main(){run(false);run(true);}
    """, "9\n9\n", False),
    ("collection extraction transfers an enum containing a handle", """
        enum Item { Job { h:runtime::Handle<Void> } }
        fn run(item:Item){match item {Item.Job{h:h}=>{drop(h.join());}}}
        fn main(){
         let mut p=pool<Item>(1);let item=p.new(Item.Job{h:runtime::thread({print(1);})});
         run(*item);
         let mut vp=pool<Vector<Item>>(1);let mut v=vp.new();
         v.push(Item.Job{h:runtime::thread({print(2);})});
         run(v.remove(0));
        }
    """, "1\n2\n", False),
    ("pool and vector preserve AsyncHandles across suspension", """
        async fn child(n:i64)->i64 {yield;n}
        async fn run(){
         let mut hp=pool<runtime::AsyncHandle<i64>>(1);
         let stored=hp.new(runtime::spawn_blocking(child(7)));
         let h=*stored;
         match h.await {Ok(n)=>{print(n);},Err(_)=>{print(0);}}
         let mut vp=pool<Vector<runtime::AsyncHandle<i64>>>(1);let mut v=vp.new();
         v.push(runtime::spawn_blocking(child(9)));
         match v.pop(){Some(next)=>{match next.await{Ok(n)=>{print(n);},Err(_)=>{print(0);}}},None=>{}}
        }
        fn main(){let h=runtime::spawn(run());drop(h.join());}
    """, "7\n9\n", False),
    ("vector reindexes the deferred effect after removing a sibling", """
        fn start(entry:&mut &mut i64,next:&mut i64)->runtime::Handle<Void>{
            runtime::thread({move entry;move next;*entry=next;})
        }
        fn main(){
            let mut a:i64=7;let mut b:i64=9;let k:i64=1;
            let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
            match m.get_mut(&k){
                Some(v)=>{
                    let mut pool=pool<Vector<runtime::Handle<Void>>>(1);let mut handles=pool.new();
                    handles.push(runtime::thread({}));
                    handles.push(start(v,&mut b));
                    let first=handles.remove(0);drop(first.join());
                    match handles.pop(){Some(h)=>{drop(h.join());},None=>{}}
                    print(**v);
                },None=>{}
            }
            match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
                    let mut pool=pool<Vector<runtime::Handle<Void>>>(1);let mut handles=pool.new();
            print(b);
        }
    """, "9\n11\n", False),
    ('pool extraction and vector pop restore handle ownership', """
        fn main(){
         let mut hp=pool<runtime::Handle<Void>>(1);
         let h=hp.new(runtime::thread({print(1);}));
         let task=*h;
         drop(task.join());
         let mut vp=pool<Vector<runtime::Handle<Void>>>(1);let mut v=vp.new();
         v.push(runtime::thread({print(2);}));
         match v.pop(){Some(next)=>{drop(next.join());},None=>{}}
         drop(hp.new(runtime::thread({print(3);})));
        }
    """, "1\n2\n3\n", False),
    ('pool extraction preserves the deferred effect through a recursive relay', """
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
           let mut pool=pool<runtime::Handle<Void>>(1);let allocation=pool.new(h);let h=*allocation;let e=relay(h,2,false);
           match e{Envelope.Empty=>{},Envelope.Waiting{h:h}=>{drop(h.join());}}
           print(**v);
          },None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ('vector remove preserves the deferred effect through a recursive relay', """
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
           match e{Envelope.Empty=>{},Envelope.Waiting{h:h}=>{drop(h.join());}}
           print(**v);
          },None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ('recursive relay completes the effect on its waiting path', """
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
           let mut pool=pool<Vector<runtime::Handle<Void>>>(1);let mut vhandles=pool.new();vhandles.push(h);let h=vhandles.remove(0);let e=relay(h,2,true);
           match e{Envelope.Empty=>{},Envelope.Waiting{h:h}=>{drop(h.join());}}
           print(**v);
          },None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ("a native handle is the indirection of a recursive enum", """
        enum Chain { End, Link { next:runtime::Handle<Chain> } }
        fn make(n:i64)->Chain {
            if n > 0 {
                let next=runtime::thread({move n;make(n-1)});
                Chain.Link{next:next}
            } else {Chain.End}
        }
        fn run(value:Chain){
            match value {
                Chain.End=>{print(7);},
                Chain.Link{next:next}=>{match next.join(){Ok(tail)=>{run(tail);},Err(_)=>{print(0);}}}
            }
        }
        fn main(){run(make(2));}
    """, "7\n", False),
    ("recursive async writer defers its effect until the inner handle completes", """
        enum Envelope{Waiting{h:runtime::AsyncHandle<Void>}}
        async fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::spawn_blocking(replace(entry,next,2));
         Envelope.Waiting{h:h}
        }
        async fn replace(entry:&mut &mut i64,next:&mut i64,n:i64){if n>0 {replace(entry,next,n-1).await;} else {yield;*entry=next;}}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=start(v,&mut b).await;match e{Envelope.Waiting{h:h}=>{drop(h.await);}}print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "9\n11\n", False),
    ("mutually recursive relay preserves the nested handle effect", """
        enum Envelope{Waiting{h:runtime::Handle<Void>}}
        fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::thread({move entry;move next;*entry=next;});
         Envelope.Waiting{h:h}
        }
        fn relay(e:Envelope,n:i64)->Envelope{if n>0 {other(e,n-1)} else {e}}
        fn other(e:Envelope,n:i64)->Envelope{relay(e,n)}
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=relay(start(v,&mut b),2);match e{Envelope.Waiting{h:h}=>{drop(h.join());}}print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ('recursive relay keeps ownership of both array elements', """
        fn pass(h:[runtime::Handle<Void>;2], n:i64)->[runtime::Handle<Void>;2] {
            if n > 0 {pass(h,n-1)} else {h}
        }
        fn main() {
            let a=runtime::thread({print(3);});
            let b=runtime::thread({print(5);});
            let pair=pass([a,b],2);
            drop(pair);
        }
    """, ['3', '5'], False),
    ('native worker captures a nested autonomous handle', """
        enum Envelope { Waiting { h:runtime::Handle<Void> } }
        fn main() {
            let inner=runtime::thread({print(3);});
            let envelope=Envelope.Waiting{h:inner};
            let outer=runtime::thread({
                move envelope;
                match envelope {Envelope.Waiting{h:h}=>{drop(h.join());}};
            });
            drop(outer.join());
        }
    """, "3\n", False),
    ('nested native handle effect follows a recursive relay', """
        enum Envelope{Waiting{h:runtime::Handle<Void>}}
        fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::thread({move entry;move next;*entry=next;});
         Envelope.Waiting{h:h}
        }
        fn relay(e:Envelope,n:i64)->Envelope{if n>0 {relay(e,n-1)} else {e}}
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=relay(start(v,&mut b),2);match e{Envelope.Waiting{h:h}=>{drop(h.join());}}print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ('nested native handle effect crosses recursive wait', """
        enum Envelope{Waiting{h:runtime::Handle<Void>}}
        fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::thread({move entry;move next;*entry=next;});
         Envelope.Waiting{h:h}
        }
        fn wait(e:Envelope,n:i64){if n>0 {wait(e,n-1);} else {match e{Envelope.Waiting{h:h}=>{drop(h.join());}}}}
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=start(v,&mut b);wait(e,2);print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ('native worker returns a handle with its effect still pending', """
        enum Envelope{Waiting{h:runtime::Handle<Void>}}
        fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::thread({move entry;move next;*entry=next;});
         Envelope.Waiting{h:h}
        }
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let next=&mut b; let outer=runtime::thread({move v;move next;start(v,next)}); match outer.join(){Ok(e)=>{match e{Envelope.Waiting{h:h}=>{drop(h.join());}}},Err(_)=>{}}},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "11\n", False),
    ('nested async handle effect crosses recursive await', """
        enum Envelope{Waiting{h:runtime::AsyncHandle<Void>}}
        async fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::spawn_blocking(replace(entry,next));
         Envelope.Waiting{h:h}
        }
        async fn replace(entry:&mut &mut i64,next:&mut i64){yield;*entry=next;}
        async fn wait(e:Envelope,n:i64){if n>0 {wait(e,n-1).await;} else {match e{Envelope.Waiting{h:h}=>{drop(h.await);}}}}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=start(v,&mut b).await;wait(e,2).await;print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "9\n11\n", False),
    ('direct await returns a blocking handle with its effect still pending', """
        enum Envelope{Waiting{h:runtime::AsyncHandle<Void>}}
        async fn start(entry:&mut &mut i64,next:&mut i64)->runtime::AsyncHandle<Void>{runtime::spawn_blocking(replace(entry,next))}
        async fn replace(entry:&mut &mut i64,next:&mut i64){yield;*entry=next;}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let h=start(v,&mut b).await;drop(h.await);print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "9\n11\n", False),
    ('failed launch through recursive await retains the original entry', """
        enum Envelope{Waiting{h:runtime::AsyncHandle<Void>}}
        async fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::spawn_blocking(replace(entry,next));
         Envelope.Waiting{h:h}
        }
        async fn replace(entry:&mut &mut i64,next:&mut i64){yield;*entry=next;}
        async fn wait(e:Envelope,n:i64){if n>0 {wait(e,n-1).await;} else {match e{Envelope.Waiting{h:h}=>{drop(h.await);}}}}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=start(v,&mut b).await;wait(e,2).await;print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n9\n", 'blocking_failure'),
    ("entry effect crosses a native handle factory", """
        fn start(entry:&mut &mut i64,next:&mut i64)->runtime::Handle<Void>{
         runtime::thread({move entry;move next;*entry=next;})
        }
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let h=start(v,&mut b);drop(h.join());print(**v);},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "9\n11\n", False),
    ("entry effect crosses an asynchronous wait contract", """
        async fn replace(entry:&mut &mut i64, next:&mut i64){yield;*entry=next;}
        async fn wait(h:runtime::AsyncHandle<Void>){drop(h.await);}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let h=runtime::spawn_blocking(replace(v,&mut b));wait(h).await;print(**v);},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "9\n11\n", False),
    ("native entry effect crosses a synchronous wait contract", """
        fn attendre(h:runtime::Handle<Void>){drop(h.join());}
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let next=&mut b;let h=runtime::thread({move v;move next;*v=next;});attendre(h);},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "11\n", False),
    ("native entry effect survives join", """
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let next=&mut b;let h=runtime::thread({move v;move next;*v=next;});drop(h.join());},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "11\n", False),
    ("failed blocking entry effect keeps the original target", """
        async fn replace(entry:&mut &mut i64, next:&mut i64){yield;*entry=next;}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let h=runtime::spawn_blocking(replace(v,&mut b));match h.await{Err(_)=>{print(**v);},Ok(())=>{print(0);}}},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(a);print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n11\n9\n", "blocking_failure"),
    ("blocking entry effect survives await", """
        async fn replace(entry:&mut &mut i64, next:&mut i64){yield;*entry=next;}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let h=runtime::spawn_blocking(replace(v,&mut b));drop(h.await);print(**v);},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "9\n11\n", False),
    ("scalar destination persists across await and yield", """
        async fn calc()->i64{let x:i64=7;let y=x;yield;y}
        async fn root(){
            let a={let x=calc().await;let y=x;yield;y};
            print(a);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n", False),
    ("a pooled ownership tree survives direct await", """
        struct Item{leaf:A<i64>}
        async fn relay(item:A<Item>)->A<Item>{yield;item}
        async fn root(){
            let mut leaves=pool<i64>(1);let mut items=pool<Item>(1);
            let item=items.new(Item{leaf:leaves.new(7)});
            let item=relay(item).await;print(*(*item).leaf);drop(item);
            let item=items.new(Item{leaf:leaves.new(9)});print(*(*item).leaf);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n9\n", False),
    ("owned nested aggregates move through direct await and release both slots", """
        struct Item{a:A<i64>}
        struct Wrap{items:[Item;2]}
        async fn child(w:Wrap)->Wrap {if true {yield;} w}
        async fn root(){
            let mut p=pool<i64>(2);
            let w=Wrap{items:[Item{a:p.new(27)},Item{a:p.new(28)}]};
            let result=child(w).await;
            print(*result.items[0].a);print(*result.items[1].a);
            drop(result);let a=p.new(33);let b=p.new(34);print(*a);print(*b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "27\n28\n33\n34\n", False),
    ("owned result can use an injected pool after the task releases its borrow", """
        struct Wrap{a:A<i64>}
        async fn child(p:&mut Pool<i64>)->Wrap{yield;Wrap{a:p.new(27)}}
        async fn root(){
            let mut p=pool<i64>(2);let w=child(&mut p).await;let a=p.new(33);
            print(*w.a);print(*a);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "27\n33\n", False),
    ("owned result from join moves out of its Ok envelope", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap)->Wrap{yield;w}
        fn main(){
            let mut p=pool<i64>(1);let w=Wrap{a:p.new(27)};
            let h=runtime::spawn(child(w));
            let result=match h.join(){Ok(v)=>{v},Err(_)=>{Wrap{a:p.new(99)}}};
            print(*result.a);drop(result);let a=p.new(33);print(*a);
        }
    """, "27\n33\n", False),
    ("inactive owning future releases its capture", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap)->Wrap{yield;w}
        fn main(){
            let mut p=pool<i64>(1);let w=Wrap{a:p.new(27)};
            let f=child(w);drop(f);let a=p.new(33);print(*a);
        }
    """, "33\n", False),
    ("join preserves a mutable result through a typed relay", """
        struct View{r:&mut i64}
        async fn child(r:&mut i64)->View{yield;View{r:r}}
        fn relay(h:runtime::Handle<View>)->runtime::Handle<View>{h}
        fn main(){
            let mut n:i64=1;let h=relay(runtime::spawn(child(&mut n)));
            let mut v=match h.join(){Ok(v)=>{v},Err(_)=>{View{r:&mut n}}};
            let r=&mut *v.r;*r=27;print(n);
        }
    """, "27\n", False),
    ("AsyncHandle parks through a nested direct await and returns a borrowed result", """
        struct View{r:&i64}
        async fn child(r:&i64)->View{yield;View{r:r}}
        async fn wait(h:runtime::AsyncHandle<View>)->i64{
            match h.await{Ok(v)=>{let r=v.r;*r},Err(_)=>{99}}
        }
        async fn root()->i64{
            let n:i64=27;
            let h=runtime::spawn_blocking(child(&n));wait(h).await
        }
        fn main(){let h=runtime::spawn(root());match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}}
    """, "27\n", "park"),
    ("completion before the parent parks is retained", """
        async fn child()->i64{yield;27}
        async fn root(){
            let h=runtime::spawn_blocking(child());
            match h.await{Ok(n)=>{print(n);},Err(_)=>{print(99);}}
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "27\n", "wake_before_park"),
    ("AsyncHandle completes with ownership of its result", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap)->Wrap{yield;w}
        async fn root(){
            let mut p=pool<i64>(1);let w=Wrap{a:p.new(27)};
            let h=runtime::spawn_blocking(child(w));
            match h.await{Ok(v)=>{print(*v.a);drop(v);},Err(_)=>{print(99);}}
            let a=p.new(33);print(*a);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "27\n33\n", False),
    ("failed blocking launch destroys the owning capture before Err", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap)->Wrap{print(99);yield;w}
        async fn root(){
            let mut p=pool<i64>(1);let w=Wrap{a:p.new(27)};
            let h=runtime::spawn_blocking(child(w));
            match h.await{Ok(v)=>{drop(v);print(98);},Err(e)=>{
                match e{runtime::Error.LaunchFailed=>{let a=p.new(33);print(*a);}}
            }}
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "33\n", "blocking_failure"),
    ("failed scheduler startup destroys owning captures before join", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap)->Wrap{print(99);w}
        fn main(){
            let mut p=pool<i64>(1);let h=runtime::spawn(child(Wrap{a:p.new(27)}));
            match h.join(){
                Ok(v)=>{drop(v);print(98);},
                Err(e)=>{match e{runtime::Error.LaunchFailed=>{let a=p.new(33);print(*a);}}}
            }
        }
    """, "33\n", True),
    ("native thread join returns a borrowed aggregate through a typed Result", """
        struct View{r:&i64}
        fn wait(h:runtime::Handle<View>)->Result<View,runtime::Error>{h.join()}
        fn main(){
            let n:i64=27;let r=&n;
            let h=runtime::thread({move r;View{r:r}});
            match wait(h){Ok(v)=>{let x=v.r;print(*x);},Err(_)=>{print(99);}}
        }
    """, "27\n", False),
    ("wildcard consuming match destroys the owning result", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap)->Wrap{yield;w}
        fn main(){
            let mut p=pool<i64>(1);let h=runtime::spawn(child(Wrap{a:p.new(27)}));
            match h.join(){Ok(_)=>{},Err(_)=>{}}
            let a=p.new(33);print(*a);
        }
    """, "33\n", False),
    ("nested await resumes branch and loop with pending operands", """
        async fn leaf(n:i64)->i64 { if n>0 {yield;yield;} n+1 }
        async fn noop(){ {yield;} }
        async fn root(n:i64)->i64 {
            let mut total:i64=0;let mut i:i64=0;
            while i<n {
                i=i+1;
                noop().await;
                if i==2 {yield;continue;}
                total=total+leaf(copy(i)).await;
            }
            total
        }
        fn main(){
            let a=runtime::spawn(root(4));let b=runtime::spawn(root(3));
            match a.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            match b.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
        }
    """, "11\n6\n", False),

    ("aggregate capture and borrowed result through nested awaits", """
        struct View{r:&i64}
        async fn leaf(v:View)->View {yield;v}
        async fn middle(v:View)->View {let pending=leaf(v);{yield;pending.await}}
        async fn root(n:i64)->i64 {let v=middle(View{r:&n}).await;let r=v.r;*r}
        fn main(){
            let h=runtime::spawn(root(17));
            match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
        }
    """, "17\n", False),
    ("await keeps only the returned field dependency", """
        struct Pair{a:&i64,b:&i64}
        struct View{r:&i64}
        async fn leaf(v:Pair)->View {yield;View{r:v.a}}
        async fn root(){
            let a:i64=1;let mut b:i64=2;
            let v=leaf(Pair{a:&a,b:&b}).await;
            b=7;let r=v.r;
            print(*r);print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "1\n7\n", False),
    ("future from a branch carries its selected result loan", """
        struct View{r:&i64}
        async fn root(take_left:bool)->i64 {
            let a:i64=10;let b:i64=20;
            let task=if take_left {leaf(&a)} else {leaf(&b)};
            let view=task.await;
            let r=view.r;*r
        }
        async fn leaf(r:&i64)->View {yield;View{r:r}}
        fn main(){
            let a=runtime::spawn(root(true));let b=runtime::spawn(root(false));
            match a.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            match b.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
        }
    """, "10\n20\n", False),
    ("repeated await releases the single child region", """
        async fn leaf(n:i64)->i64 {yield;n}
        async fn root(){
            #(stack_region:max_size=4K,count=1) {
                let mut i:i64=0;
                while i<4 {print(leaf(copy(i)).await);i=i+1;}
            }
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "0\n1\n2\n3\n", False),
    ("retained handle and mutable capture through a call", """
        fn wait(h:runtime::Handle<i64>)->i64 {match h.join(){Ok(n)=>{n},Err(_)=>{0}}}
        fn main(){
            let mut n:i64=1;let r=&mut n;
            let h=runtime::thread({move r;*r=8;*r});
            print(3);print(wait(h));print(n);
        }
    """, "3\n8\n8\n", False),
    ("dependent handle escapes only into a surviving receiver", """
        fn main(){
            let n:i64=7;
            let h=#(stack_region:max_size=1K,count=1){let r=&n;runtime::thread({move r;*r})};
            print(n);match h.join(){Ok(n)=>{print(n);},Err(_)=>{print(0);}}
        }
    """, "7\n7\n", False),
    ("abandoned native thread drains after main", """
        fn main(){
            let h=#(stack_region:max_size=1K,count=1){runtime::thread({print(11);})};
            drop(h);
            let other=runtime::thread({print(22);});
        }
    """, ["11", "22"], False),
    ("async locals survive more than one poll", """
        async fn calc(n:i64)->i64 {
            let mut x=n+1;yield;x=x+2;yield;if x>0 {x}else{0}
        }
        fn main(){
            let a=calc(4);let b=calc(9);print(0);
            let h1=runtime::spawn(a);let h2=runtime::spawn(b);
            match h1.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            match h2.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
        }
    """, "0\n7\n12\n", False),
    ("dropping an inactive future returns its region", """
        #(datastack:region_stack_size=1K,region_size=1K)
        async fn work(n:i64){yield;print(n);}
        fn main(){
            let a=work(99);drop(a);
            let b=work(7);let h=runtime::spawn(b);
            match h.join(){Ok(())=>{print(8);},Err(_)=>{print(0);}}
        }
    """, "7\n8\n", False),
    ("abandoned future keeps running after yield", """
        async fn work(n:i64){yield;print(n);yield;print(3);}
        fn main(){runtime::spawn(work(2));}
    """, "2\n3\n", False),

    ("transferred vector keeps its data address across suspension and growth", """
        async fn grow(mut v:A<Vector<i64>>)->A<Vector<i64>>{
            yield;v.push(9);v
        }
        async fn root(){
            let mut p=pool<Vector<i64>>(1);
            let v=#(stack_region:max_size=4K,count=2){
                let mut v=p.new();v.push(7);v
            };
            let v=grow(v).await;print(v[0]);print(v[1]);drop(v);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n9\n", False),

    ("a transferred vector returns through spawn and join", """
        async fn grow(mut v:A<Vector<i64>>)->A<Vector<i64>>{yield;v.push(9);v}
        fn main(){
            let mut p=pool<Vector<i64>>(1);
            let h=#(stack_region:max_size=4K,count=2){
                let mut v=p.new();v.push(7);runtime::spawn(grow(v))
            };
            match h.join(){Ok(v)=>{print(v[0]);print(v[1]);drop(v);},Err(_)=>{print(0);}}
        }
    """, "7\n9\n", False),
    ("a transferred string grows on the blocking worker", """
        async fn grow(mut s:A<String>)->A<String>{yield;s.push_str("a");s}
        async fn root(){
            let mut p=pool<String>(1);
            let s=#(stack_region:max_size=4K,count=1){
                let mut s=p.new();s.push_str("é");s
            };
            let h=runtime::spawn_blocking(grow(s));
            match h.await{Ok(s)=>{print(s.byte_len());drop(s);},Err(_)=>{print(0);}}
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "3\n", False),
    ("a transferred vector returns its stored borrow", """
        async fn relay(v:A<Vector<&i64>>)->A<Vector<&i64>>{yield;v}
        async fn root(){
            let mut n:i64=7;let mut p=pool<Vector<&i64>>(1);let mut v=p.new();
            v.push(&n);let v=relay(v).await;
            let r=v[0];print(*r);drop(v);n=9;print(n);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n9\n", False),

    ("async map moves through direct await and a blocking handle", """
        async fn grow(mut m:HashMap<i64,i64>)->HashMap<i64,i64>{
            yield;drop(m.insert(2,9));m
        }
        async fn root(){
            let mut m=HashMap<i64,i64>::new();
            drop(m.insert(1,7));
            let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
            let m=grow(m).await;
            let h=runtime::spawn_blocking(grow(m));
            match h.await{
                Ok(m)=>{
                    let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
                    let k:i64=2;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
                    drop(m);
                },
                Err(_)=>{print(0);}
            }
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "7\n7\n9\n", False),
    ("a map result can move after join", """
        async fn pass(m:HashMap<i64,i64>)->HashMap<i64,i64>{yield;m}
        fn main(){
            let mut m=HashMap<i64,i64>::new();drop(m.insert(1,7));
            let h=runtime::spawn(pass(m));let r=h.join();
            let r={r};
            match r{
                Ok(m)=>{let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}},
                Err(_)=>{print(0);}
            }
        }
    """, "7\n", False),
    ("failed blocking launch releases a captured map", """
        #(datastack:region_stack_size=8K,region_size=4K)
        async fn consume(m:HashMap<i64,i64>){drop(m);}
        async fn root(){
            let mut m=HashMap<i64,i64>::new();drop(m.insert(1,7));
            let h=runtime::spawn_blocking(consume(m));
            match h.await{Ok(())=>{print(0);},Err(_)=>{print(1);}}
            let mut m=HashMap<i64,i64>::new();drop(m.insert(1,9));
            let k:i64=1;match m.get(&k){Some(v)=>{print(*v);},None=>{print(0);}}
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "1\n9\n", "blocking_failure"),

    ("two suspended tasks keep independent growing contents", """
        async fn work(n:i64)->i64 {
            let mut p=pool<Vector<i64>>(1);let mut v=p.new();
            v.push(n);yield;v.push(3);yield;v[0]+v[1]
        }
        fn main(){
            let h1=runtime::spawn(work(4));let h2=runtime::spawn(work(9));
            match h1.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
            match h2.join(){Ok(n)=>{print(n);},Err(_)=>{print(99);}}
        }
    """, "7\n12\n", False),
    ("abandoned future keeps and releases a local string", """
        async fn work(){
            let mut p=pool<String>(1);let mut text=p.new();text.push_str("é");
            yield;text.push_str("a");print(text.byte_len());
        }
        fn main(){runtime::spawn(work());}
    """, "3\n", False),

    ("async borrow and local region survive suspension", """
        async fn bump(n:&mut i64)->i64 {
            let mut p=pool<Vector<i64>>(1);let mut v=p.new();v.push(*n);
            yield;*n=v[0]+3;*n
        }
        fn main(){
            let mut n:i64=4;let mut m:i64=0;let r=&mut m;
            let t=runtime::thread({move r;*r=9;});
            let f=bump(&mut n);let h=runtime::spawn(f);
            drop(t.join());print(m);
            match h.join(){Ok(x)=>{print(x);},Err(_)=>{print(0);}}
            print(n);
        }
    """, "9\n7\n7\n", False),
    ("scheduler startup failure releases the future", """
        #(datastack:region_stack_size=1K,region_size=1K)
        async fn work(n:&mut i64){*n=99;}
        fn main(){
            let mut n:i64=7;
            let h=runtime::spawn(work(&mut n));match h.join(){Ok(())=>{},Err(_)=>{print(1);}}
            print(n);
            let h=runtime::spawn(work(&mut n));match h.join(){Ok(())=>{},Err(_)=>{print(2);}}
            print(n);
        }
    """, "1\n7\n2\n7\n", True),
]

REJECTED = [
    ("pending async method prevents destruction of the receiver",
     ASYNC_METHOD.replace("            drop(source);", "").replace(
         "let count = reading.await;", "drop(source); let count = reading.await;"),
     "emprunt actif"),
    ("pending async method prevents writes to the destination",
     ASYNC_METHOD.replace("let count = reading.await;", "buffer[0] = 7; let count = reading.await;"),
     "emprunt actif"),
    ("early break retains the remaining handle reservation", """
        fn run(second:bool) {
            let mut nombre:i64=7;
            let vue=&mut nombre;
            let mut pool=pool<Vector<runtime::Handle<Void>>>(1);
            let mut handles=pool.new();
            handles.push(runtime::thread({move vue;*vue=9;}));
            if second { handles.push(runtime::thread({})); }
            loop {
                match handles.pop() {
                    Some(h)=>{drop(h.join());break;},
                    None=>{break;}
                }
            }
            print(nombre);
        }
        fn main(){run(false);run(true);}
    """, "emprunt actif"),
    ("dropping a vector cannot abandon a dependent handle", """
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
           let mut pool=pool<Vector<runtime::Handle<Void>>>(1);let mut vhandles=pool.new();vhandles.push(h);drop(vhandles);let e=Envelope.Empty;
           match e{Envelope.Empty=>{},Envelope.Waiting{h:h}=>{drop(h.join());}}
           print(**v);
          },None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, "ne peut pas être abandonné"),
    ('nested dependent handle cannot be discarded', """
        enum Envelope{Waiting{h:runtime::Handle<Void>}}
        fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::thread({move entry;move next;*entry=next;});
         Envelope.Waiting{h:h}
        }
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=start(v,&mut b);match e{Envelope.Waiting{h:_}=>{}}print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, 'ne peut pas être abandonné'),
    ('return from recursive relay does not complete the handle', """
        enum Envelope{Waiting{h:runtime::Handle<Void>}}
        fn start(entry:&mut &mut i64,next:&mut i64)->Envelope{
         let h=runtime::thread({move entry;move next;*entry=next;});
         Envelope.Waiting{h:h}
        }
        fn relay(e:Envelope,n:i64)->Envelope{if n>0 {relay(e,n-1)} else {e}}
        fn main(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let e=relay(start(v,&mut b),2);print(**v);match e{Envelope.Waiting{h:h}=>{drop(h.join());}}print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
    """, 'emprunt actif'),
    ('direct await of a factory does not complete the returned handle', """
        enum Envelope{Waiting{h:runtime::AsyncHandle<Void>}}
        async fn start(entry:&mut &mut i64,next:&mut i64)->runtime::AsyncHandle<Void>{runtime::spawn_blocking(replace(entry,next))}
        async fn replace(entry:&mut &mut i64,next:&mut i64){yield;*entry=next;}
        async fn root(){
         let mut a:i64=7;let mut b:i64=9;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){
           Some(v)=>{let h=start(v,&mut b).await;print(**v);drop(h.await);print(**v);},
           None=>{}
         }
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}
         print(b);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, 'emprunt actif'),
    ("a deferred entry replacement cannot install a shorter reference", """
        async fn replace(entry:&mut &mut i64, next:&mut i64){yield;*entry=next;}
        async fn root(){
         let mut a:i64=7;let k:i64=1;
         let mut m=HashMap<i64,&mut i64>::new();drop(m.insert(1,&mut a));
         match m.get_mut(&k){Some(v)=>{let mut b:i64=9;let h=runtime::spawn_blocking(replace(v,&mut b));drop(h.await);print(**v);},None=>{}}
         match m.remove(&k){Some(v)=>{*v=11;},None=>{}}

        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "survivrait"),
    ("a returned vector keeps its target borrowed", """
        async fn relay(v:A<Vector<&i64>>)->A<Vector<&i64>>{yield;v}
        async fn root(){
            let mut n:i64=7;let mut p=pool<Vector<&i64>>(1);let mut v=p.new();
            v.push(&n);let v=relay(v).await;
            n=9;let r=v[0];print(*r);drop(v);
        }
        fn main(){let h=runtime::spawn(root());drop(h.join());}
    """, "emprunt actif"),
    ("a task holding a vector cannot escape its source pool", """
        async fn grow(mut v:A<Vector<i64>>)->A<Vector<i64>>{
            yield;v.push(9);v
        }
        fn main(){
            let h={
                let mut p=pool<Vector<i64>>(1);
                let v=p.new();runtime::spawn(grow(v))
            };
            drop(h.join());
        }
    """, "la dépendance ne survit pas à la sortie du bloc"),
    ("join result still reserves the captured target", """
        struct View{r:&mut i64}
        async fn child(r:&mut i64)->View{yield;View{r:r}}
        fn main(){
            let mut n:i64=1;let h=runtime::spawn(child(&mut n));
            match h.join(){Ok(v)=>{print(n);let q=v.r;print(*q);},Err(_)=>{}}
        }
    """, "emprunt actif"),
    ("owner cannot return a slot from a pool in its own frame", """
        struct Wrap{a:A<i64>}
        async fn child()->Wrap{let mut p=pool<i64>(1);Wrap{a:p.new(27)}}
        fn main(){}
    """, "cible locale"),
    ("owning inactive future prevents dropping its source pool", """
        struct Wrap{a:A<i64>}
        async fn child(w:Wrap){drop(w);}
        fn main(){let mut p=pool<i64>(1);let f=child(Wrap{a:p.new(27)});drop(p);}
    """, "pool porte encore"),
    ("AsyncHandle cannot be awaited twice", """
        async fn child(){yield;}
        async fn root(){let h=runtime::spawn_blocking(child());drop(h.await);drop(h.await);}
        fn main(){}
    """, "déjà déplacée"),
    ("spawn_blocking cannot be called in main", """
        async fn child(){} fn main(){let h=runtime::spawn_blocking(child());}
    """, "exige un contexte async"),
    ("await cannot suspend main", """
        async fn f()->i64{1} fn main(){print(f().await);}
    """, "contexte async"),
    ("a non-void awaited result cannot be silently discarded", """
        async fn f()->i64{1} async fn g(){f().await;} fn main(){}
    """, "exige un receveur"),
    ("await consumes the child", """
        async fn f(){yield;} async fn g(){let child=f();child.await;child.await;} fn main(){}
    """, "déjà déplacée"),
    ("awaited aggregate cannot return a child-local reference", """
        struct View{r:&i64}
        async fn child()->View {let n:i64=0;yield;View{r:&n}}
        fn main(){}
    """, "cible locale"),
    ("returned aggregate reserves its mutable target", """
        struct View{r:&mut i64}
        async fn child(v:View)->View {yield;v}
        async fn root(){
            let mut n:i64=1;let mut v=child(View{r:&mut n}).await;
            print(n);let r=&mut *v.r;*r=8;
        }
        fn main(){}
    """, "emprunt actif"),

    ("mutable capture blocks caller read", """
        fn main(){
            let mut n:i64=0;let r=&mut n;let h=runtime::thread({move r;*r=1;});
            print(n);drop(h.join());
        }
    """, "emprunt actif"),
    ("returned native handle preserves exclusive capture", """
        fn start(r:&mut i64)->runtime::Handle<()> {runtime::thread({move r;*r=1;})}
        fn main(){let mut n:i64=0;let h=start(&mut n);print(n);drop(h.join());}
    """, "emprunt actif"),
    ("scope cannot abandon a dependent handle", """
        fn main(){let n:i64=0;let r=&n;let h=runtime::thread({move r;*r});}
    """, "doit être joint"),
    ("dependent handle cannot outlive captured local", """
        fn main(){
            let h={let n:i64=0;let r=&n;runtime::thread({move r;*r})};drop(h.join());
        }
    """, "sortie du bloc"),
    ("continue cannot abandon a dependent handle", """
        fn main(){let n:i64=0;loop {let r=&n;let h=runtime::thread({move r;*r});continue;}}
    """, "doit être joint"),

    ("inactive future reserves its mutable capture", """
        async fn f(x:&mut i64){yield;*x=3;}
        fn main(){
            let mut n:i64=1;let f=f(&mut n);print(n);
            let h=runtime::spawn(f);drop(h.join());
        }
    """, "emprunt actif"),
    ("spawned future cannot abandon a dependent capture", """
        async fn f(x:&mut i64){yield;*x=3;}
        fn main(){let mut n:i64=1;runtime::spawn(f(&mut n));}
    """, "ne peut pas être abandonné"),
    ("join consumes the handle", """
        fn main(){let h=runtime::thread({1});drop(h.join());drop(h.join());}
    """, "déjà déplacée"),
]

FAILED_CREATE = r"""
static int test_pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                               void *(*start)(void *), void *argument) {
    (void)thread; (void)attr; (void)start; (void)argument;
    return 1;
}
#define pthread_create test_pthread_create
"""


def emit(source):
    return subprocess.run([FRONTEND, "emit-c"], input=source, text=True, capture_output=True)


def main():
    for name, program, expected in REJECTED:
        result = emit(program)
        assert result.returncode != 0 and expected in result.stderr, (name, result.stderr)
    print(f"{len(REJECTED)} refus confirmés")

    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "test.c"
        binary = Path(temporary) / "test"
        for name, program, expected, inject_failure in ACCEPTED:
            result = emit(program)
            assert result.returncode == 0, (name, result.stderr)
            generated = result.stdout
            if name == "scalar destination persists across await and yield":
                assert "= &frame->result;" in generated
                assert "crust_future_take(t0, o1, sizeof(*o1));" in generated
                assert "= &scalarr" in generated
            if name in (
                "transferred vector keeps its data address across suspension and growth",
                "a transferred vector returns through spawn and join",
                "a transferred string grows on the blocking worker",
            ):
                append = "    if (count > value->band->limit - value->used)"
                element = "    if (index >= value->used / size)"
                assert append in generated and element in generated
                generated = generated.replace(append, """
    if (value->used == 0) {
        test_growing_address = crust_region_data(value);
    } else if (crust_region_data(value) != test_growing_address) {
        abort();
    }
""" + append)
                anchor = "static inline __attribute__((unused)) void crust_region_append("
                assert anchor in generated
                generated = generated.replace(anchor, "static const void *test_growing_address;\n" + anchor)
                generated = generated.replace(element, """
    if (crust_region_data(value) != test_growing_address)
        abort();
""" + element)
            if name == "async map moves through direct await and a blocking handle":
                anchor = "    return slot == 0 ? NULL : crust_region_data(&map->contents)"
                assert generated.count(anchor) == 1
                generated = generated.replace(anchor, """
    static const void *entry_address;
    if (key == 1 && slot != 0) {
        const void *current = crust_region_data(&map->contents)
            + slot + crust_map_round(sizeof(CrustMapEntry));
        if (entry_address == NULL)
            entry_address = current;
        else if (entry_address != current)
            abort();
    }
""" + anchor)
            if name == "repeated await releases the single child region":
                take = "CrustGrowing region = dedicated ? crust_region_take_dedicated() : crust_region_take();"
                assert take in generated
                # Refuse spill to a dedicated band: all four children must reuse slot 0.
                generated = generated.replace(take, take + """
    if (crust_region_scope != NULL &&
        (region.band != crust_region_scope || region.slot != 0))
        abort();
""")
            if inject_failure in ("park", "wake_before_park"):
                # Force the dedicated worker to finish on the selected side of
                # the transition between registering the waiter and parking.
                anchor = "static CRUST_LOCAL CrustHandle *crust_poll_root;"
                assert anchor in generated
                generated = generated.replace(anchor, "static atomic_bool test_worker_ready;\n" + anchor)
                anchor = "static void *crust_async_blocking_worker(void *argument) {"
                assert anchor in generated
                generated = generated.replace(anchor, anchor + "\n    while (!atomic_load(&test_worker_ready)) {}")
                if inject_failure == "park":
                    anchor = "handle->parked = parked;"
                    assert anchor in generated
                    generated = generated.replace(anchor, anchor + "\n            if (parked) atomic_store(&test_worker_ready, true);")
                else:
                    anchor = "        return -1;\n    }\n    pthread_mutex_unlock(&crust_threads_lock);"
                    assert anchor in generated
                    generated = generated.replace(anchor, """
        atomic_store(&test_worker_ready, true);
        while (atomic_load(&handle->status) != CRUST_COMPLETE) {}
""" + anchor)
            elif inject_failure == "blocking_failure":
                anchor = "pthread_create(&handle->thread, NULL, crust_async_blocking_worker, handle)"
                assert anchor in generated
                generated = generated.replace(anchor,
                    "((void)crust_async_blocking_worker, 1)")
            elif inject_failure:
                generated = generated.replace("#include <pthread.h>", "#include <pthread.h>\n" + FAILED_CREATE, 1)
            source.write_text(generated)
            for opt in ("-O0", "-O2"):
                subprocess.run(
                    ["cc", "-std=c11", opt, "-pthread", "-Wall", "-Wextra", "-Werror",
                     "-fsanitize=undefined", "-fno-sanitize-recover=all", source, "-lm", "-o", binary],
                    check=True,
                )
                result = subprocess.run([binary], text=True, capture_output=True, timeout=20)
                actual = sorted(result.stdout.splitlines()) if isinstance(expected, list) else result.stdout
                assert result.returncode == 0 and actual == expected, (name, result)
            print(f"{name} OK")


if __name__ == "__main__":
    main()
