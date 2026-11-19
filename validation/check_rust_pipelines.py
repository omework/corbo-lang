#!/usr/bin/env python3
"""Compare fluent iterator ownership and collection with both compilers."""

import argparse
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from compiler_location import compiler_root
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"

SOURCE = """
struct Counter { position: i64 }
impl Counter {
    fn next(&mut self) -> Option<i64> {
        let value = (*self).position;
        if copy(value) == 3 { return None; }
        let position = &mut (*self).position;
        *position = copy(value) + 1;
        Some(value)
    }
}
"""

APPEND = """
let mut source = Counter { position: 0 };
let mut storage = pool<Vector<i64>>(1);
let mut destination = storage.new();
destination.push(99);
Iter::new(&mut source).map(|x: i64| { x * 10 }).collect(&mut destination);
print(destination.len());
print(destination[0]);
print(destination[2]);
print(source.position);
"""

ACCEPTED = [
    ("an inferred floating-point capture is copied into the mapper", """
        let mut source = Counter { position: 2 };
        let factor = 1.5;
        let mut mapper = Iter::new(&mut source).map(|x: i64| { drop(x); factor * 2.0 });
        match mapper.next() { Some(value) => { print(value); }, None => {} }
        print(factor);
    """, "3\n1.5\n"),
    ("mapper copies primitive captures once and keeps its own mutable state", """
        let mut source = Counter { position: 1 };
        let mut offset = 10;
        let mut mapper = Iter::new(&mut source).map(|x: i64| {
            offset = offset + 1;
            x + offset
        });
        offset = 20;
        match mapper.next() { Some(value) => { print(value); }, None => {} }
        match mapper.next() { Some(value) => { print(value); }, None => {} }
        print(offset);
    """, "12\n14\n20\n"),
    ("move captures a primitive and keeps its modifications across calls", """
        let mut source = Counter { position: 1 };
        let mut offset = 10;
        let mut mapper = Iter::new(&mut source).map(move |x: i64| {
            offset = offset + 1;
            x + offset
        });
        match mapper.next() { Some(value) => { print(value); }, None => {} }
        match mapper.next() { Some(value) => { print(value); }, None => {} }
    """, "12\n14\n"),
    ("each capturing mapper retains its predecessor and has separate state", """
        let mut source = Counter { position: 1 };
        let mut offset = 10;
        let extra = 100;
        let first = Iter::new(&mut source).map(move |x: i64| {
            offset = offset + 1;
            x + offset
        });
        let mut second = first.map(|x: i64| { x + extra });
        match second.next() { Some(value) => { print(value); }, None => {} }
        match second.next() { Some(value) => { print(value); }, None => {} }
        print(source.position);
    """, "112\n114\n3\n"),
    ("collect appends and releases the source", APPEND, "4\n99\n10\n3\n"),
    ("next and chained maps are lazy and infer each output type", """
        let mut source = Counter { position: 1 };
        let first = Iter::new(&mut source);
        let mut mapper = first.map(|x: i64| -> bool { print(x); x == 2 });
        print(8);
        match mapper.next() { Some(flag) => { print(flag); }, None => { print(99); } }
        let mut storage = pool<Vector<u8>>(1);
        let mut destination = storage.new();
        mapper.map(|flag: bool| -> u8 { if flag { 23 } else { 24 } })
            .collect(&mut *destination);
        print(destination[0]);
        print(source.position);
    """, "8\n1\nfalse\n2\n23\n3\n"),
    ("empty source never executes the mapper", """
        let mut source = Counter { position: 3 };
        let mut storage = pool<Vector<i64>>(1);
        let mut destination = storage.new();
        Iter::new(&mut source).map(|x: i64| { print(99); x })
            .collect(&mut destination);
        print(destination.len());
    """, "0\n"),
    ("iter itself can be advanced and collected", """
        let mut source = Counter { position: 1 };
        let mut iter = Iter::new(&mut source);
        match iter.next() { Some(item) => { print(item); }, None => { print(99); } }
        let mut storage = pool<Vector<i64>>(1);
        let mut destination = storage.new();
        iter.collect(&mut destination);
        print(destination[0]);
    """, "1\n2\n"),
    ("the source is available after the last manual next", """
        let mut source = Counter { position: 0 };
        let mut mapper = Iter::new(&mut source).map(|x: i64| { x + 10 });
        match mapper.next() { Some(item) => { print(item); }, None => { print(99); } }
        print(source.position);
    """, "10\n1\n"),
    ("a fluent temporary and a pipeline moved out of a result block", """
        let mut source = Counter { position: 0 };
        match Iter::new(&mut source).map(|x: i64| { x + 10 }).next() {
            Some(item) => { print(item); }, None => { print(99); }
        }
        let mut iter = { Iter::new(&mut source) };
        match iter.next() { Some(item) => { print(item); }, None => { print(99); } }
        print(source.position);
    """, "10\n1\n2\n"),
    ("collect may grow a vector after the last use of its slice", """
        let mut source = Counter { position: 2 };
        let mut storage = pool<Vector<i64>>(1);
        let mut destination = storage.new();
        destination.push(8);
        let view = &destination[..];
        print(view[0]);
        Iter::new(&mut source).collect(&mut destination);
        print(destination[1]);
    """, "8\n2\n"),
]

REJECTED = [
    ("moved predecessor", """
        let mut source = Counter { position: 0 };
        let mut iter = Iter::new(&mut source);
        let mapper = iter.map(|x: i64| { x * 10 });
        let item = iter.next();
        drop(item);
        drop(mapper);
    """, "déplacée"),
    ("source read while pipeline still uses its loan", """
        let mut source = Counter { position: 0 };
        let mut mapper = Iter::new(&mut source).map(|x: i64| { x * 10 });
        print(source.position);
        let item = mapper.next();
        drop(item);
    """, "emprunt actif"),
    ("pipeline escapes its source", """
        let mut mapper = { let mut source = Counter { position: 0 };
            Iter::new(&mut source).map(|x: i64| { x * 10 })
        };
        let item = mapper.next();
        drop(item);
    """, "dépendance ne survit pas"),
    ("wrong map input", """
        let mut source = Counter { position: 0 };
        let mapper = Iter::new(&mut source).map(|x: bool| { x });
        drop(mapper);
    """, "type de l’item"),
    ("wrong collection element", """
        let mut source = Counter { position: 0 };
        let mut storage = pool<Vector<bool>>(1);
        let mut destination = storage.new();
        Iter::new(&mut source).collect(&mut destination);
    """, "type des items"),
    ("shared destination", """
        let mut source = Counter { position: 0 };
        let mut storage = pool<Vector<i64>>(1);
        let destination = storage.new();
        Iter::new(&mut source).collect(&destination);
    """, "Vector emprunté en &mut"),
    ("append with a live destination loan", """
        let mut source = Counter { position: 0 };
        let mut storage = pool<Vector<i64>>(1);
        let mut destination = storage.new();
        destination.push(8);
        let view = &destination[..];
        Iter::new(&mut source).collect(&mut destination);
        print(view[0]);
    """, "emprunt actif"),
]



GENERIC = [
    ("collect moves nominal elements", SOURCE + """
        struct Item { code: i64 }
        fn main() {
            let mut source = Counter { position: 0 };
            let mut storage = pool<Vector<Item>>(1);
            let mut destination = storage.new();
            Iter::new(&mut source).map(|x: i64| -> Item { Item { code: x + 10 } })
                .collect(&mut destination);
            print(destination.len());
            drop(destination);
            print(source.position);
        }
    """, "3\n3\n"),
    ("collect moves enum variants", SOURCE + """
        enum Item { Code { code: i64 }, Empty }
        fn main() {
            let mut source = Counter { position: 0 };
            let mut storage = pool<Vector<Item>>(1);
            let mut destination = storage.new();
            Iter::new(&mut source).map(|x: i64| -> Item { Item.Code { code: x + 10 } })
                .collect(&mut destination);
            print(destination.len());
            drop(destination);
            print(source.position);
        }
    """, "3\n3\n"),
    ("next moves a record into map", """
        struct Item { code: i64 }
        struct Source { position: i64 }
        impl Source {
            fn next(&mut self) -> Option<Item> {
                let value = (*self).position;
                if copy(value) == 2 { return None; }
                let place = &mut (*self).position;
                *place = copy(value) + 1;
                Some(Item { code: value })
            }
        }
        fn main() {
            let mut source = Source { position: 0 };
            let mut storage = pool<Vector<i64>>(1);
            let mut destination = storage.new();
            Iter::new(&mut source).map(|item: Item| -> i64 { item.code + 10 })
                .collect(&mut destination);
            print(destination[0]);
            print(destination[1]);
        }
    """, "10\n11\n"),
    ("fixed-array elements move from map to collect", SOURCE + """
        fn main() {
            let mut source = Counter { position: 0 };
            let mut storage = pool<Vector<[i64; 2]>>(1);
            let mut destination = storage.new();
            let mut pipeline = Iter::new(&mut source).map(|value: i64| -> [i64; 2] {
                let pieces: [i64; 2] = [value, 7];
                pieces
            });
            match pipeline.next() {
                Some(row) => { print(row[1]); },
                None => {}
            }
            pipeline.collect(&mut destination);
            print(destination.len());
            print(source.position);
        }
    """, "7\n2\n3\n"),
    ("drop cleans mapped values exactly once", SOURCE + """
        struct Item { code: i64 }
        impl Item { fn drop(&mut self) { print((*self).code); } }
        fn main() {
            let mut source = Counter { position: 0 };
            let mut pipeline = Iter::new(&mut source).map(|x: i64| -> Item { Item { code: x + 10 } });
            let first = pipeline.next();
            drop(first);
            {
                let second = pipeline.next();
            }
            drop(pipeline);
            print(source.position);
        }
    """, "10\n11\n2\n"),
]

BORROWED_ITEM = """
struct Counter { position: i64 }
impl Counter {
    fn next(&mut self) -> Option<&i64> { Some(&(*self).position) }
}
fn main() {
    let mut source = Counter { position: 8 };
    let mut pipeline = Iter::new(&mut source).map(|view: &i64| -> &i64 { view });
    let received = pipeline.next();
    let item = received;
    match item { Some(view) => { print(*view); }, None => {} }
    print(source.position);
}
"""



BORROWED_MUTABLE = (BORROWED_ITEM
    .replace("Option<&i64>", "Option<&mut i64>")
    .replace("Some(&(*self)", "Some(&mut (*self)")
    .replace("|view: &i64| -> &i64", "|view: &mut i64| -> &mut i64")
    .replace("print(*view);", "*view = 11; print(*view);")
)

BORROWED_HANDLE = (BORROWED_ITEM
    .replace("|view: &i64| -> &i64 { view }",
             "|view: &i64| -> runtime::Handle<i64> { runtime::thread({ move view; *view }) }")
    .replace("Some(view) => { print(*view); }", """Some(handle) => {
        match handle.join() {
            Ok(value) => { print(value); }, Err(_) => { print(99); }
        }
    }""")
)

BORROWED_MUTABLE_HANDLE = (BORROWED_HANDLE
    .replace("Option<&i64>", "Option<&mut i64>")
    .replace("Some(&(*self)", "Some(&mut (*self)")
    .replace("|view: &i64|", "|view: &mut i64|")
    .replace("move view; *view", "move view; *view = 12; *view")
)

INFERRED_HANDLE_CALL = (
    "fn launch(view: &i64) -> runtime::Handle<i64> { runtime::thread({ move view; *view }) }\n"
    "fn forward(view: &i64) -> runtime::Handle<i64> { launch(view) }\n"
    + BORROWED_HANDLE.replace(
        "|view: &i64| -> runtime::Handle<i64> { runtime::thread({ move view; *view }) }",
        "|view: &i64| { forward(view) }",
    )
)

BORROWED_RECORD = """
struct Item { code: i64 }
struct Source { child: Item }
impl Source {
    fn next(&mut self) -> Option<&Item> { Some(&(*self).child) }
}
fn main() {
    let mut source = Source { child: Item { code: 8 } };
    let mut pipeline = Iter::new(&mut source).map(|view: &Item| -> &Item { view });
    let envelope = pipeline.next();
    match envelope {
        Some(view) => { print((*view).code); },
        None => { print(99); }
    }
    print(source.child.code);
}
"""

BORROWED_SLICE = """
struct Source { bytes: [u8; 3] }
impl Source {
    fn next(&mut self) -> Option<&[u8]> { Some(&(*self).bytes[..2]) }
}
fn main() {
    let mut source = Source { bytes: [4, 5, 6] };
    let mut pipeline = Iter::new(&mut source).map(|view: &[u8]| { view });
    let received = pipeline.next();
    let moved = received;
    match moved {
        Some(view) => { print(view.len()); print(view[1]); },
        None => { print(99); }
    }
    print(source.bytes[0]);
}
"""

MAPPED_SLICE = BORROWED_SLICE.replace(
    "|view: &[u8]| { view }", "|view: &[u8]| -> &[u8] { &view[0..1] }"
).replace("print(view[1]);", "print(view[0]);")

MUTABLE_SLICE = (BORROWED_SLICE
    .replace("&[u8]", "&mut [u8]")
    .replace("Some(&(*self)", "Some(&mut (*self)")
    .replace("print(view.len()); print(view[1]);", "view[0] = 9; print(view[0]);")
)

DYNAMIC_SLICE = (BORROWED_SLICE
    .replace("bytes: [u8; 3]", "bytes: [u8; 3], end: u64")
    .replace("bytes[..2]", "bytes[..(*self).end]")
    .replace("fn main()", "fn run(end: u64)")
    .replace("bytes: [4, 5, 6]", "bytes: [4, 5, 6], end: end")
    + "\nfn main() { run(4); }\n"
)

RECORD_SLICE = """
struct Cell { value: i64 }
struct Source { items: [Cell; 2] }
impl Source {
    fn next(&mut self) -> Option<&[Cell]> { Some(&(*self).items[..2]) }
}
fn main() {
    let mut source = Source { items: [Cell { value: 4 }, Cell { value: 7 }] };
    let mut pipeline = Iter::new(&mut source)
        .map(|view: &[Cell]| -> &[Cell] { &view[1..2] });
    let item = pipeline.next();
    let moved = item;
    match moved { Some(view) => { print(view[0].value); }, None => {} }
}
"""

ARRAY_ROW_SLICE = """
struct Source { items: [[i64; 2]; 2] }
impl Source {
    fn next(&mut self) -> Option<&[[i64; 2]]> { Some(&(*self).items[..2]) }
}
fn main() {
    let mut source = Source { items: [[4, 5], [7, 8]] };
    let mut pipeline = Iter::new(&mut source).map(|view: &[[i64; 2]]| { view });
    match pipeline.next() { Some(view) => { print(view[1][0]); }, None => {} }
}
"""

MUTABLE_RECORD_SLICE = (RECORD_SLICE
    .replace("&[Cell]", "&mut [Cell]")
    .replace("Some(&(*self)", "Some(&mut (*self)")
    .replace("{ &view[1..2] }", "{ &mut view[1..2] }")
    .replace("print(view[0].value);", "view[0] = Cell { value: 12 }; print(view[0].value);")
    .replace("None => {} }\n", "None => {} }\n    print(source.items[1].value);\n")
)

COLLECT_EXTERNAL_REFERENCE = """
struct Source { value: &i64, consumed: i64 }
impl Source {
    fn next(&mut self) -> Option<&i64> {
        let old = (*self).consumed;
        if copy(old) == 2 { return None; }
        let flag = &mut (*self).consumed;
        *flag = old + 1;
        Some(&*(*self).value)
    }
}
fn main() {
    let number = 7;
    let mut source = Source { value: &number, consumed: 0 };
    let mut memory = pool<Vector<&i64>>(1);
    let mut destination = memory.new();
    Iter::new(&mut source).map(|item: &i64| { item }).collect(&mut destination);
    drop(source);
    let view = destination[1];
    print(*view);
}
"""

NESTED_REFERENCE = """
struct Source { item: i64 }
impl Source {
    fn next(&mut self) -> Option<&i64> { Some(&(*self).item) }
}
fn main() {
    let mut source = Source { item: 7 };
    let mut pipeline = Iter::new(&mut source)
        .map(|view: &i64| -> Option<Option<&i64>> { Some(Some(view)) });
    let result = pipeline.next();
    let moved = result;
    match moved {
        Some(envelope) => {
            match envelope {
                Some(inner) => { match inner { Some(view) => { print(*view); }, None => {} } },
                None => {}
            }
        },
        None => {}
    }
    print(source.item);
}
"""

NESTED_HANDLE = (
    "fn launch(view: &i64) -> runtime::Handle<i64> { runtime::thread({ move view; *view }) }\n"
    + NESTED_REFERENCE
    .replace("-> Option<Option<&i64>> { Some(Some(view)) }",
             "-> Option<runtime::Handle<i64>> { Some(launch(view)) }")
    .replace("""            match envelope {
                Some(inner) => { match inner { Some(view) => { print(*view); }, None => {} } },
                None => {}
            }""",
             """            match envelope {
                Some(handle) => {
                    match handle.join() { Ok(value) => { print(value); }, Err(_) => { print(99); } }
                },
                None => {}
            }""")
)

INFERRED_REFERENCE_CALL = (
    "fn relay(view: &i64) -> &i64 { view }\n"
    + BORROWED_ITEM.replace("|view: &i64| -> &i64 { view }", "|view: &i64| { relay(view) }")
)

OPTION_ALLOCATION = """
fn create(memory: &mut Pool<i64>) -> Option<A<i64>> {
    Some(memory.new(42))
}
fn main() {
    let mut memory = pool<i64>(1);
    let first = create(&mut memory);
    let moved = first;
    match moved {
        Some(item) => { print(*item); drop(item); },
        None => { print(99); }
    }
    let next = memory.new(7);
    print(*next);
}
"""

COLLECT_HANDLES = """
struct Counter { position: i64 }
impl Counter {
    fn next(&mut self) -> Option<i64> {
        let x = (*self).position;
        if copy(x) == 2 { return None; }
        let pos = &mut (*self).position;
        *pos = copy(x) + 1;
        Some(x)
    }
}
fn main() {
    let mut counter = Counter { position: 0 };

    let mut storage = pool<Vector<runtime::Handle<i64>>>(1);
    let mut destination = storage.new();
    let stage = Iter::new(&mut counter)
        .map(|x: i64| -> runtime::Handle<i64> { runtime::thread({ move x; x + 30 }) });

    stage.collect(&mut destination);
    loop {
        match destination.pop() {
            Some(handle) => { drop(handle.join()); },
            None => { break; }
        }
    }
    print(counter.position);
}
"""


COLLECT_ALLOCATIONS = """
struct Source { memory: &mut Pool<i64>, position: i64 }
impl Source {
    fn next(&mut self) -> Option<A<i64>> {
        let value = (*self).position;
        if copy(value) == 2 { return None; }
        let position = &mut (*self).position;
        *position = copy(value) + 1;
        let memory = &mut *(*self).memory;
        Some(memory.new(value))
    }
}
fn main() {
    let mut source_memory = pool<i64>(2);
    let mut source = Source { memory: &mut source_memory, position: 0 };
    let mut destination_memory = pool<Vector<A<i64>>>(1);
    let mut destination = destination_memory.new();
    Iter::new(&mut source).map(|item: A<i64>| -> A<i64> { item }).collect(&mut destination);
    print(*destination[1]);
    drop(destination);
    drop(source);
    let recycled = source_memory.new(12);
    let another = source_memory.new(13);
    print(*recycled);
    print(*another);
}
"""

COLLECT_NOMINAL_ALLOCATIONS = """
struct Item { code: i64 }
impl Item { fn drop(&mut self) { print((*self).code); } }
struct Source { memory: &mut Pool<Item>, position: i64 }
impl Source {
    fn next(&mut self) -> Option<A<Item>> {
        let value = (*self).position;
        if copy(value) == 2 { return None; }
        let position = &mut (*self).position;
        *position = copy(value) + 1;
        let memory = &mut *(*self).memory;
        Some(memory.new(Item { code: value }))
    }
}
fn main() {
    let mut source_memory = pool<Item>(2);
    let mut source = Source { memory: &mut source_memory, position: 0 };
    let mut destination_memory = pool<Vector<A<Item>>>(1);
    let mut destination = destination_memory.new();
    Iter::new(&mut source).map(|item: A<Item>| { item }).collect(&mut destination);
    let item = destination.remove(1);
    print((*item).code);
    drop(item);
    drop(destination);
    drop(source);
    let a = source_memory.new(Item { code: 12 });
    let b = source_memory.new(Item { code: 13 });
    print((*a).code);
    print((*b).code);
}
"""

ASYNC_HANDLE_ITEM = """
struct Source { pending: A<Vector<runtime::AsyncHandle<i64>>> }
impl Source {
    fn next(&mut self) -> Option<runtime::AsyncHandle<i64>> { (*self).pending.pop() }
}
async fn task(n: i64) -> i64 { yield; n }
async fn produce() -> runtime::AsyncHandle<i64> {
    runtime::spawn_blocking(task(7))
}
async fn consume(h: runtime::AsyncHandle<i64>) {
    match h.await { Ok(n) => { print(n); }, Err(_) => { print(99); } }
}
fn main() {
    let execution = runtime::spawn(produce());
    match execution.join() {
        Ok(h) => {
            let mut storage = pool<Vector<runtime::AsyncHandle<i64>>>(1);
            let mut pending = storage.new();
            pending.push(h);
            let mut source = Source { pending: pending };
            let mut pipeline = Iter::new(&mut source).map(|h: runtime::AsyncHandle<i64>| { h });
            match pipeline.next() {
                Some(h) => { let finish = runtime::spawn(consume(h)); drop(finish.join()); },
                None => { print(97); }
            }
            match pipeline.next() { Some(h) => { drop(h); }, None => { print(8); } }
        },
        Err(_) => { print(98); }
    }
}
"""

COLLECT_ASYNC_HANDLES = """
struct Source { pending: A<Vector<runtime::AsyncHandle<i64>>> }
impl Source {
    fn next(&mut self) -> Option<runtime::AsyncHandle<i64>> { (*self).pending.pop() }
}
async fn task(n: i64) -> i64 { yield; print(n); n }
async fn run() {
    let mut storage = pool<Vector<runtime::AsyncHandle<i64>>>(1);
    let mut pending = storage.new();
    pending.push(runtime::spawn_blocking(task(7)));
    let mut source = Source { pending: pending };
    let mut output_pool = pool<Vector<runtime::AsyncHandle<i64>>>(1);
    let mut output = output_pool.new();
    Iter::new(&mut source).map(|h: runtime::AsyncHandle<i64>| { h }).collect(&mut output);
    drop(output);
}
fn main() { let handle = runtime::spawn(run()); drop(handle.join()); }
"""

DEPENDENT_ASYNC_HANDLE = """
struct Source { pending: A<Vector<runtime::AsyncHandle<i64>>> }
impl Source {
    fn next(&mut self) -> Option<runtime::AsyncHandle<i64>> { (*self).pending.pop() }
}
async fn task(n: &mut i64) -> i64 { yield; *n = 7; *n }
async fn run() {
    let mut number = 6;
    let mut storage = pool<Vector<runtime::AsyncHandle<i64>>>(1);
    let mut pending = storage.new();
    pending.push(runtime::spawn_blocking(task(&mut number)));
    let mut source = Source { pending: pending };
    let mut pipeline = Iter::new(&mut source)
        .map(|h: runtime::AsyncHandle<i64>| { h });
    match pipeline.next() {
        Some(h) => { match h.await { Ok(n) => { print(n); }, Err(_) => { print(99); } } },
        None => { print(98); }
    }
    print(number);
}
fn main() { let h = runtime::spawn(run()); drop(h.join()); }
"""

TWO_DEPENDENT_ASYNC_HANDLES = (
    DEPENDENT_ASYNC_HANDLE.replace("*n = 7", "*n = *n + 1")
    .replace("    let mut number = 6;", "    let mut first = 5;\n    let mut number = 6;")
    .replace("    pending.push(runtime::spawn_blocking(task(&mut number)));",
             "    pending.push(runtime::spawn_blocking(task(&mut first)));\n"
             "    pending.push(runtime::spawn_blocking(task(&mut number)));")
    .replace("    print(number);", """    print(number);
    match pipeline.next() {
        Some(h) => { match h.await { Ok(n) => { print(n); }, Err(_) => { print(99); } } },
        None => { print(98); }
    }
    print(first);""")
)

ESCAPING_ASYNC_HANDLE = """
async fn work(n: &i64) -> i64 { yield; *n }
async fn make() -> runtime::AsyncHandle<i64> {
    let number = 5;
    runtime::spawn_blocking(work(&number))
}
fn main() {
    let handle = runtime::spawn(make());
    drop(handle.join());
}
"""

OWNED_CAPTURE = SOURCE + """
struct Capture { n: i64 }
impl Capture { fn drop(&mut self) { print((*self).n); } }
fn main() {
    let mut source = Counter { position: 2 };
    let capture = Capture { n: 7 };
    let mut memory = pool<Vector<i64>>(1);
    let mut destination = memory.new();
    Iter::new(&mut source).map(move |item: i64| { item + capture.n }).collect(&mut destination);
    print(destination[0]);
}
"""

BORROWED_CAPTURE = SOURCE + """
fn main() {
    let mut source = Counter { position: 1 };
    let mut number = 10;
    let view = &mut number;
    let mut pipeline = Iter::new(&mut source).map(move |item: i64| {
        *view = *view + 1;
        item + *view
    });
    match pipeline.next() { Some(item) => { print(item); }, None => {} }
    match pipeline.next() { Some(item) => { print(item); }, None => {} }
    print(number);
}
"""

DEPENDENT_ACCEPTED = [
    ("shared pipeline reference after a move", BORROWED_ITEM, "8\n8\n"),
    ("mutable pipeline reference after a move", BORROWED_MUTABLE, "11\n11\n"),
    ("pipeline reference to a record field", BORROWED_RECORD, "8\n8\n"),
    ("infer a reference result through an ordinary call", INFERRED_REFERENCE_CALL, "8\n8\n"),
    ("move an inferred shared slice through the pipeline", BORROWED_SLICE, "2\n5\n4\n"),
    ("reborrow a subslice in the mapper", MAPPED_SLICE, "1\n4\n4\n"),
    ("mutate through a moved pipeline slice", MUTABLE_SLICE, "9\n9\n"),
    ("move and reborrow a slice of records", RECORD_SLICE, "7\n"),
    ("replace an element through a moved mutable record slice", MUTABLE_RECORD_SLICE, "12\n12\n"),
    ("infer the type of a slice of array rows", ARRAY_ROW_SLICE, "7\n"),
    ("collect shared references whose target is outside the source", COLLECT_EXTERNAL_REFERENCE, "7\n"),
    ("preserve a reference through nested options and a move", NESTED_REFERENCE, "7\n7\n"),
    ("preserve a pending worker through nested options until join", NESTED_HANDLE, "7\n7\n"),
    ("mapped handle releases its reference at join", BORROWED_HANDLE, "8\n8\n"),
    ("infer a forwarded handle and preserve its capture until join", INFERRED_HANDLE_CALL, "8\n8\n"),
    ("mapped handle writes through its mutable reference", BORROWED_MUTABLE_HANDLE, "12\n12\n"),
    ("collect then drain autonomous handles", COLLECT_HANDLES, "2\n"),
    ("map an AsyncHandle removed from a source field and await it", ASYNC_HANDLE_ITEM, "7\n8\n"),
    ("collect autonomous AsyncHandles and let the runtime finish them", COLLECT_ASYNC_HANDLES, "7\n"),
    ("await a mapped AsyncHandle before reading its mutable capture", DEPENDENT_ASYNC_HANDLE, "7\n7\n"),
    ("awaiting one mapped AsyncHandle releases only its selected target",
     TWO_DEPENDENT_ASYNC_HANDLES, "7\n7\n6\n6\n"),
    ("collect cleans an owned mapper capture once", OWNED_CAPTURE, "7\n9\n"),
    ("a moved mapper reference reserves the target through its last use", BORROWED_CAPTURE, "12\n14\n12\n"),
    ("collect pooled items and reuse both slots after dropping the vector",
     COLLECT_ALLOCATIONS.replace("|item: A<i64>| -> A<i64>", "|item: A<i64>|"), "1\n12\n13\n"),
    ("collect named allocations, extract one, and run each destructor once",
     COLLECT_NOMINAL_ALLOCATIONS, "1\n1\n0\n12\n13\n13\n12\n"),
    ("moved Option retains its allocation pool and returns the slot", OPTION_ALLOCATION, "42\n7\n"),
]

DEPENDENT_REJECTED = [
    ("read the capture of the remaining handle after awaiting its sibling",
     TWO_DEPENDENT_ASYNC_HANDLES.replace("    print(number);", "    print(first);"),
     5, "emprunt actif"),
    ("read the mutable capture of a mapped AsyncHandle before await",
     DEPENDENT_ASYNC_HANDLE.replace("Some(h) => { match", "Some(h) => { print(number); match"),
     5, "emprunt actif"),
    ("abandon a dependent AsyncHandle after mapping it",
     DEPENDENT_ASYNC_HANDLE.replace(
         "match h.await { Ok(n) => { print(n); }, Err(_) => { print(99); } }", "drop(h);"),
     8, "abandonné"),
    ("return an AsyncHandle whose task still borrows a local", ESCAPING_ASYNC_HANDLE, 4, "cible locale"),
    ("return an AsyncHandle whose task still borrows a parameter passed by value",
     ESCAPING_ASYNC_HANDLE.replace("async fn make()", "async fn make(number: i64)")
     .replace("    let number = 5;\n", "").replace("runtime::spawn(make())", "runtime::spawn(make(5))"),
     4, "cible locale"),
    ("read while a captured mutable reference is still live",
     BORROWED_CAPTURE.replace("    match pipeline.next()", "    print(number);\n    match pipeline.next()", 1),
     5, "emprunt actif"),
    ("use a primitive after moving it into a mapper",
     SOURCE + """
        fn main() {
            let mut source = Counter { position: 1 };
            let offset = 10;
            let mapper = Iter::new(&mut source).map(move |x: i64| { x + offset });
            print(offset);
            drop(mapper);
        }
     """, 6, "déplacée"),
    ("advance while a reference inside a nested option is still needed",
     NESTED_REFERENCE.replace("    match moved", "    let extra = pipeline.next();\n    drop(extra);\n    match moved"),
     5, "réemprunt actif"),
    ("abandon a dependent handle inside nested options",
     NESTED_HANDLE.split("    match moved")[0] + "    drop(moved);\n}\n",
     8, "abandonné"),
    ("drop the target of an independently collected reference",
     COLLECT_EXTERNAL_REFERENCE.replace("    drop(source);", "    drop(source);\n    drop(number);"),
     5, "emprunt actif"),
    ("advance while a moved record slice is still needed",
     RECORD_SLICE.replace("    match moved", "    let extra = pipeline.next();\n    drop(extra);\n    match moved"),
     5, "réemprunt actif"),
    ("mismatch the length of a row in an array slice mapper",
     ARRAY_ROW_SLICE.replace("|view: &[[i64; 2]]|", "|view: &[[i64; 3]]|"),
     1, "type de l’item"),
    ("abandon an inferred handle forwarded through another function",
     INFERRED_HANDLE_CALL.split("    match item")[0] + "    drop(item);\n}\n", 8, "abandonné"),
    ("advance before the last use of a moved slice",
     BORROWED_SLICE.replace("    match moved", "    let another = pipeline.next();\n    drop(another);\n    match moved"),
     5, "réemprunt actif"),
    ("form a slice past the end of an array field",
     BORROWED_SLICE.replace("bytes[..2]", "bytes[..4]"),
     1, "borne de tranche hors du tableau"),
    ("next before last use of its returned reference",
     BORROWED_ITEM.replace("    match item", "    let other = pipeline.next();\n    drop(other);\n    match item"),
     5, "emprunt"),
    ("reuse of a moved Option",
     BORROWED_ITEM.replace("    match item", "    drop(received);\n    match item"), 6, "déplacée"),
    ("returning a reference to a local through Some", """
        fn bad(ignored: &i64) -> Option<&i64> { let local = 4; Some(&local) }
        fn main() {}
    """, 4, "locale"),
    ("next before joining the mapped handle",
     BORROWED_HANDLE.replace("    match item", "    let extra = pipeline.next();\n    drop(extra);\n    match item"),
     5, "emprunt"),
    ("source read while a mapped handle holds a mutable reference",
     BORROWED_MUTABLE_HANDLE.replace("    match item", "    print(source.position);\n    match item"),
     5, "emprunt"),
    ("abandonment of a mapped dependent handle",
     BORROWED_HANDLE.split("    match item")[0] + "    drop(item);\n}\n", 8, "abandonné"),
    ("drop a pool while a collected item still owns its slot",
     COLLECT_ALLOCATIONS.split("    drop(destination);")[0]
     + "    drop(source);\n    drop(source_memory);\n    drop(destination);\n}\n",
     7, "pool"),
    ("drop the named pool while the vector still owns its slots",
     COLLECT_NOMINAL_ALLOCATIONS.split("    let item = destination.remove")[0]
     + "    drop(source);\n    drop(source_memory);\n    drop(destination);\n}\n",
     7, "pool"),
    ("drop pool before extracting allocation",
     OPTION_ALLOCATION.replace("    match moved", "    drop(memory);\n    match moved")
                      .split("    let next")[0] + "}\n", 7, "pool"),
]


def program(body):
    return SOURCE + "\nfn main() {\n" + body + "\n}\n"


def scalar_pipeline_cases():
    for ty in ("i32", "i64", "u8", "u16", "u32", "u64", "usize", "f32", "f64", "bool"):
        value = "true" if ty == "bool" else "1.5" if ty.startswith("f") else "1"
        yield f"collects {ty}", program(f"""
            let mut source = Counter {{ position: 2 }};
            let mut storage = pool<Vector<{ty}>>(1);
            let mut destination = storage.new();
            Iter::new(&mut source).map(|item: i64| -> {ty} {{ drop(item); {value} }})
                .collect(&mut destination);
            print(destination[0]);
        """), value + "\n"


USE_STD_ITER = False
NATIVE_ONLY = False


def iterator_source(source):
    if source is not None and USE_STD_ITER and "Iter::" in source:
        implementation = (ROOT / "stdlib/src/iter/iter.crb").read_text() + "\n"
        implementation = re.sub(r"\b(Map|Filter|Reduce|iter)\b", lambda m: "__corbo_iter_" + m[0], implementation)
        if source.startswith("#(datastack:"):
            directive, rest = source.split("\n", 1)
            return directive + "\n" + implementation + rest
        return implementation + source
    return source


def frontend(*args, source=None, check=True):
    source = iterator_source(source)
    try:
        return subprocess.run(
            [FRONTEND, *args], text=True, input=source, capture_output=True, check=check
        )
    except subprocess.CalledProcessError as error:
        print(error.stderr, file=sys.stderr, flush=True)
        raise


def run_c(root, name, generated, expected, status=0, stderr=""):
    (root / "main.c").write_text(generated)
    for opt in ("-O0", "-O2"):
        executable = root / "main"
        subprocess.run(
            [os.environ.get("CC", "cc"), "-std=c11", opt, "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
             "-fno-sanitize-recover=undefined", "-pthread", str(root / "main.c"),
             "-o", str(executable)],
            check=True,
        )
        run = subprocess.run([executable], text=True, capture_output=True, timeout=10)
        assert (run.returncode, run.stdout, run.stderr) == (status, expected, stderr), (name, opt, run)


def crustc_file(compiler, root, source, mode):
    path = root / "input.crb"
    path.write_text(iterator_source(source))
    return subprocess.run([compiler, mode, path], text=True, capture_output=True, timeout=30)


def compare_c(compiler, root, name, source, expected, status=0, stderr=""):
    rust = None if NATIVE_ONLY else frontend("emit-c", source=source).stdout
    native = crustc_file(compiler, root, source, "--emit-c")
    assert native.returncode == 0 and native.stdout.startswith("#"), (name, native)
    if rust is not None:
        run_c(root, f"Rust frontend: {name}", rust, expected, status, stderr)
    run_c(root, f"corboc: {name}", native.stdout, expected, status, stderr)


def check_failed_blocking_launch(compiler, root, source, expected):
    rust = None if NATIVE_ONLY else frontend("emit-c", source=source).stdout
    native = crustc_file(compiler, root, source, "--emit-c")
    assert native.returncode == 0 and native.stdout.startswith("#"), native
    for name, generated, call, failure in (
        ("Rust frontend", rust,
         "pthread_create(&handle->thread, NULL, crust_async_blocking_worker, handle)",
         "((void)crust_async_blocking_worker, 1)"),
        ("corboc", native.stdout, "pthread_create(&thread,&attr,run_blocking,task)",
         "((void)&thread, (void)run_blocking, 1)"),
    ):
        if generated is None:
            continue
        assert generated.count(call) == 1, name
        run_c(root, name, generated.replace(call, failure), expected)


def check_rejected(compiler, root, name, source, rule, message):
    if not NATIVE_ONLY:
        result = frontend("check", source=source, check=False)
        assert result.returncode and message in result.stderr, (name, result.stderr)
    for mode in ("--verify", "--emit-c"):
        native = crustc_file(compiler, root, source, mode)
        diagnostic = native.stdout.splitlines()
        assert native.returncode == 8 and diagnostic[0:1] == [str(rule)], (name, mode, native)
    print(f"rejected by {'corboc' if NATIVE_ONLY else 'both'}: {name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corboc", type=Path, help="reuse a freshly built corboc")
    parser.add_argument("--std-iter", action="store_true", help="exercise the actual generic Iter implementation")
    parser.add_argument("--native-only", action="store_true", help="use corboc without invoking the frozen Rust compiler")
    args = parser.parse_args()
    if args.native_only and not args.corboc:
        parser.error("--native-only requires --corboc")
    global USE_STD_ITER, NATIVE_ONLY
    USE_STD_ITER = args.std_iter
    NATIVE_ONLY = args.native_only
    with tempfile.TemporaryDirectory(prefix="crust-pipeline-") as temp:
        root = Path(temp)
        compiler = args.corboc.resolve() if args.corboc else root / "corboc"
        if not args.corboc:
            frontend("build", str(compiler_root()), "-o", str(compiler))
        for name, body, expected in ACCEPTED:
            compare_c(compiler, root, name, program(body), expected)
            print(f"accepted by {'corboc' if NATIVE_ONLY else 'both'}: {name}", flush=True)
        for name, source, expected in (*GENERIC, *scalar_pipeline_cases()):
            compare_c(compiler, root, name, source, expected)
            print(f"accepted by {'corboc' if NATIVE_ONLY else 'both'}: {name}", flush=True)
        for name, source, expected in DEPENDENT_ACCEPTED:
            compare_c(compiler, root, name, source, expected)
            print(f"accepted by {'corboc' if NATIVE_ONLY else 'both'}: {name}", flush=True)
        for name, source, rule, message in DEPENDENT_REJECTED:
            check_rejected(compiler, root, name, source, rule, message)
        rules = [6, 5, 4, 1, 1, 5, 5]
        for (name, body, diagnostic), rule in zip(REJECTED, rules, strict=True):
            source = program(body)
            check_rejected(compiler, root, name, source, rule, diagnostic)
        recursive = SOURCE + """
        fn visit(level: i64) {
            if copy(level) > 0 { visit(level - 1); }
            let mut source = Counter { position: 2 };
            let mut storage = pool<Vector<i64>>(1);
            let mut destination = storage.new();
            Iter::new(&mut source).map(|x: i64| { x + 10 }).collect(&mut destination);
            print(destination[0]);
        }
        fn main() { visit(2); }
        """
        compare_c(compiler, root, "recursive verification", recursive, "12\n12\n12\n")
        print("accepted: a pipeline inside a recursive function")
        exhausted = ("#(datastack: region_size=1K)\n" + program(APPEND)).replace("copy(value) == 3", "copy(value) == 129")
        compare_c(compiler, root, "regional limit", exhausted, "",
              status=1, stderr="corbo: limite de la datastack à régions\n")
        print("runtime: collect respects the existing region limit")
        compare_c(compiler, root, "dynamic field slice bound", DYNAMIC_SLICE, "",
                  status=1, stderr="corbo: borne de tranche hors du tableau\n")
        print("runtime: field slice checks its dynamic bound")
        check_failed_blocking_launch(compiler, root, ASYNC_HANDLE_ITEM, "99\n8\n")
        check_failed_blocking_launch(compiler, root, DEPENDENT_ASYNC_HANDLE, "99\n6\n")
        print("runtime: mapped AsyncHandles preserve failed blocking launches")
        (root / "src").mkdir()
        (root / "package.toml").write_text('[package]\nname = "example"\n')
        (root / "src/main.crb").write_text(
            "use std::iter::Iter as Walk;\n" + program(APPEND.replace("Iter::", "Walk::"))
        )
        if not NATIVE_ONLY:
            frontend("build", str(root), "-o", str(root / "package-example"))
            run = subprocess.run([root / "package-example"], check=True, capture_output=True, text=True, timeout=10)
            assert (run.stdout, run.stderr) == ("4\n99\n10\n3\n", "")
        native = subprocess.run(
            [compiler, "--emit-package-c", root, "--stdlib-dir", ROOT / "stdlib/src"],
            check=True, capture_output=True, text=True, timeout=30
        )
        run_c(root, "corboc package", native.stdout, "4\n99\n10\n3\n")
        if sys.platform == "darwin" and os.uname().machine == "arm64":
            installation = root / "install"
            installed = installation / "bin/corboc"
            installed.parent.mkdir(parents=True)
            shutil.copy2(compiler, installed)
            bundled = installation / "share/corbo/stdlib/src"
            bundled.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "stdlib/src", bundled)
            executable = root / "native-package-example"
            subprocess.run([installed, "build", root, "-o", executable], check=True, timeout=30)
            run = subprocess.run([executable], check=True, capture_output=True, text=True, timeout=10)
            assert (run.stdout, run.stderr) == ("4\n99\n10\n3\n", "")
        print(f"accepted by {'corboc' if NATIVE_ONLY else 'both'}: std::iter::Iter import with alias in a package", flush=True)


if __name__ == "__main__":
    main()
