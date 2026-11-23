# Corbo

**An experimental systems programming language built around developer intent, predictable memory management, and static verification.**

[Français](README-fr.md)

Language, STD and runtime: [omework/corbo-lang](https://github.com/omework/corbo-lang).
Compiler: [omework/corboc](https://github.com/omework/corboc).

## Contents

- [How Corbo's philosophy evolved](#how-corbos-philosophy-evolved)
- [Memory budgets in practice](#memory-budgets-in-practice)
- [Getting started](#getting-started)
- [Language and STD examples](#language-and-std-examples)
- [Explore the STD](#explore-the-std)
- [Source layout and runtime boundary](#source-layout-and-runtime-boundary)
- [Build the compiler from source](#build-the-compiler-from-source)
- [Documentation and validation status](#documentation-and-validation-status)
- [API references: STD](docs/STDLIB.md) · [runtime](docs/RUNTIME.md)

<a id="philosophy"></a>

## How Corbo's philosophy evolved

Corbo began as an experiment in designing a systems programming language primarily for AI-generated code.

The initial idea was simple: **developer intent is a resource that a compiler should exploit.**

Corbo prioritizes explicit, machine-checkable constraints over ease of authoring, while aiming to keep the resulting code understandable and auditable by humans.

Memory management became one of the central experiments.

**Memory is finite. We know it, yet we often write programs as if it were unlimited.**

Corbo explores what happens when programs are designed around explicit memory capacities, predictable lifetimes, and bounded allocation strategies, without relying on a general-purpose heap allocator.

At first, this was primarily a question of feasibility: how much software could reasonably be built under these constraints?

As the language and its standard library developed, another possibility began to emerge.

**What if AI could use the constraints of an entire system to help determine how that system should be implemented?**

Business requirements, payload limits, communication patterns, concurrency bounds, and resource budgets could potentially inform not only individual allocations, but entire software architectures.

These inputs do not all provide the same guarantees. An expected workload is an assumption; an enforced capacity is a limit. Their distinction matters: an implementation may be optimized around assumptions, while its guarantees must rest on constraints the program actually enforces.

AI agents could use this information to generate specialized implementations adapted to known requirements. Explicit contracts would make those choices inspectable, while the compiler verifies the properties it can establish and runtime checks enforce limits that cannot be resolved statically.

This was not the original motivation behind Corbo's memory model. It emerged through experimentation.

It remains a hypothesis, not an established result.

Cheaper code generation does not remove the cost of validation, maintenance, or understanding a system. Corbo explores whether explicit constraints and compiler verification can help make specialization practical without making its consequences harder to assess.

Corbo is an attempt to explore that hypothesis: **what becomes possible when software generation becomes cheaper, constraints are explicit, and verification is part of the programming model?**

## Memory budgets in practice

### An implicit memory budget in Rust

This Rust program collects 1,000 integers and prints the number stored:

<!-- corpus: rust-only -->
```rust
fn main() {
    let count: i64 = 1000;
    let mut numbers = Vec::new();
    for number in 0..count {
        numbers.push(number);
    }
    println!("{}", numbers.len());
}
```

The vector grows as needed. Its growth budget and the policy for exceeding that
budget are left implicit in this program. Rust lets the developer add limits;
this example does not express one.

### An explicit growth budget in Corbo

The same collection can make its storage budget part of the source.
Here `count` is `1000` to keep both examples runnable; it can come from input
without changing the declared budget:

<!-- example: budget -->
```rust
use std::Vector;

fn main() {
    let count: i64 = 1000;
    let mut vectors = Pool<Vector<i64>>::new(1);

    #(stack_region: max_size=64K, count=1) {
        let mut numbers = vectors.new();
        let mut number: i64 = 0;
        while number < count {
            numbers.push(number);
            number += 1;
        }
        print(numbers.len());
    }
}
```

Output: `1000`. [Complete package](examples/features/budget/).

- `Pool<Vector<i64>>::new(1)` provides one vector slot. The `1` counts vector
  objects, not their elements.
- `#(stack_region: max_size=64K, count=1)` sets a 64 KiB region size and reserves
  one region for this scope. The vector's growing payload uses that region.
- An `i64` occupies eight bytes, so this payload budget holds at most 8,192
  elements. Increasing the number of inputs does not increase the region limit.
- With `push`, exceeding that limit stops the program with a diagnostic.
  Scope exit destroys the vector before making its region storage reusable.

The limit applies to the element storage; the descriptor, pool and runtime
metadata have their own storage. This is not a total-process memory limit.

**The explicit annotation is optional today.** When a size is omitted, Corbo
uses a statically inferred bound where available, then its configured/default
region policy. A growing value still has a finite region limit. This example
shows how a developer supplies a particular limit directly in the code.

## Getting started

You need a compatible `corboc` and a host C11 toolchain. If you need to build the
compiler, follow [the source-build instructions](#build-the-compiler-from-source)
below; the current compiler requires an existing compatible self-hosted seed.

Clone the language repository, then build and run the first example:

```sh
git clone git@github.com:omework/corbo-lang.git
cd corbo-lang
```

From this language checkout:

```sh
cd examples/features/hello
corboc build
./build/feature_demo
```

It prints `42`. To create a package in your working directory:

```sh
corboc new my_package
cd my_package
corboc build
./build/my_package
```

The scaffold includes `package.toml`, an empty `src/main.crb`, `.gitignore` and
a README. Edit `src/main.crb` to add your program. Existing paths are never
overwritten, and Git is not initialized. Package names use letters, digits
and underscores, starting with a letter or underscore; `std` and `runtime`
are reserved.

You can also create the manifest manually:


<!-- example-file: modules/package.toml -->
```toml
[package]
name="feature_demo"
```

Save a complete program as `src/main.crb`, as shown in the
[first example](#hello). From the directory containing `package.toml`, run:

```sh
corboc build
./build/feature_demo
```

The compiler creates `build/` and names the binary after `[package].name`.
To choose another binary name, add this optional section to `package.toml`:

```toml
[bin]
name = "my-program"
```

The output becomes `build/my-program`; an omitted `[bin]` or `[bin].name`
keeps the package name. The name is a filename component, not a path: letters,
digits, `_`, `-` and `.` are accepted, with at least one letter, digit or `_`.

An explicit package path keeps the default output inside that package.
`-o` overrides the configured name and writes to the specified path relative
to your current directory:

```sh
corboc build ./my-package
corboc build -o my-program
corboc build ./my-package -o my-program
```

Check the package without generating C or a binary:

```sh
corboc check
corboc check path/to/package --watch
corboc check src/main.crb --watch
```

`--watch` checks immediately, then rechecks after saves to project `.crb` files
and manifests. It stays alive after errors and ignores generated directories.
Imported modules, transitive local path dependencies and installed STD sources
are watched too. Manifest edits refresh the dependency graph; pinned Git
revisions change through their manifest, without polling network repositories.
A file inside `src/` uses its enclosing package context and checks the complete
package. A standalone file uses the installed STD and need not define `main`;
unrelated neighboring files are ignored. No C or binary is generated by check.
Stop with Ctrl-C. Existing verifier diagnostics are retained; analysis is not
incremental.

The filename policy adds `.exe` on Windows. The native `build` driver currently
supports macOS ARM64; other native build drivers remain to be implemented.
The installed compiler finds its matching STD under `share/corbo/stdlib/src`.
[Editor support](ide/README.md) provides `.crb` highlighting for Vim, Neovim and
VS Code.

## Language and STD examples

Start with the basics, then follow values through borrowing, storage,
composition and concurrent execution. Each program is complete and has a
package under [`examples/features/`](examples/features/README.md), including the
[memory-budget example](#an-explicit-growth-budget-in-corbo) above.
The examples are synchronized with their source and validated with `corboc`;
[validation status](#documentation-and-validation-status) records the scope.

- [Basics](#basics): [A synchronous entry point](#hello), [Primitives and checked operators](#numbers), [Expressions and control flow](#control), [Functions, tuples and destructuring](#tuples), [Structs, constants and receiver modes](#methods), [Enums and pattern matching](#enums), [Result, Option and early propagation](#errors).
- [Memory and lifetimes](#memory-and-lifetimes): [Moves and primitive copies](#moves), [Shared borrows and mutable reborrows](#borrows), [Fixed arrays, structural repetition and slices](#arrays), [Fixed-capacity pools and allocation handles](#pools), [Receivers and placement across scopes](#placement), [Destruction before storage release](#destruction), [Datastack budgets, local regions and page reclamation](#regions).
- [Collections and pipelines](#collections-and-pipelines): [Vectors and extraction](#vector), [HashMap lookup, replacement and removal](#map), [UTF-8 text and caller-owned bytes](#text), [Bounded inline strings](#bounded-text), [Closures and explicit callable passing](#closures), [STD iterator pipelines](#iter).
- [Generic code and packages](#generic-code-and-packages): [Contracts on generic structs](#generic), [Static structural type contracts](#contracts), [Packages, modules, visibility and aliases](#modules), [Conditional compilation](#target).
- [Async and threads](#async-and-threads): [Futures, suspension and execution branches](#async), [Native threads and captured loans](#threads), [Blocking work from an async context](#blocking).
- [STD in practice](#std-in-practice): [Async files](#async-file), [Blocking files, errors and caller-provided buffers](#file), [Buffered I/O through structural contracts](#buffered), [Typed network endpoints and datagrams](#network), [Hashes and encodings with bounded output](#encoding), [Binary endianness](#binary), [Monotonic time](#time), [Async timers](#async-time), [Compression with an explicit workspace](#compression).
- [Native interop](#native-interop): [Unchecked C, typed operands and native assembly](#foreign).

### Basics

<a id="hello"></a>

#### A synchronous entry point

`main` is synchronous. Build a package with `package.toml` and `src/main.crb`.

<!-- example: hello -->
```rust
fn main() {
    print(42);
}
```

Output: `42`. [Complete package](examples/features/hello/).

<a id="numbers"></a>

#### Primitives and checked operators

Integers default to `i64`, decimal floating-point literals to `f64`. Variables in arithmetic must have compatible types. `as` checks that the actual numeric value is exactly representable and stops the program on failure; `try_from` returns a recoverable `Result`. Integer arithmetic, shifts and indexing retain their checks.

Postfix `!` extracts `Ok(value)` or `Some(value)` and stops on `Err`/`None`.
Use `?` to propagate failure instead. Each operator evaluates its operand once.

<!-- example: checked_extraction -->
```rust
fn main() {
    let length: usize = 42;
    let encoded = length as u16;

    let fallible = u16::try_from(length);
    let unwrapped = fallible!;

    print(encoded);
    print(unwrapped);
}
```

<!-- example: numbers -->
```rust
fn main() {
    let byte: u8 = 21;
    let wide: u64 = byte as u64;
    let ratio: f32 = 1.5;
    let mut flags: u32 = 1;
    flags <<= 3;
    flags |= 2;
    print(wide * 2);
    print(flags & 8);
    print(ratio == 1.5);
}
```

Output: `42, 8, true`. [Complete package](examples/features/numbers/).

<a id="control"></a>

#### Expressions and control flow

Blocks, `if`, `match` and `loop` can produce values. Semicolons distinguish statements from trailing values. `continue` and `break` clean up the scopes they leave.

<!-- example: control -->
```rust
fn main() {
    let selected = if true { 40 } else { 0 };
    let mut total: i64 = 0;
    let mut index: i64 = 0;

    while index < 4 {
        index += 1;
        if index == 2 { continue; }
        total += index;
    }

    let result = loop {
        break selected + 2;
    };

    print(total);
    print(result);
}
```

Output: `8, 42`. [Complete package](examples/features/control/).

<a id="tuples"></a>

#### Functions, tuples and destructuring

Functions can return tuples of two or more values. Types are inferred by position when no binding annotation is supplied.

<!-- example: tuples -->
```rust
fn measurements(value: i64) -> (i64, i64, bool) {
    (value + 1, value * 2, value > 0)
}

fn main() {
    let (next, doubled, positive) = measurements(21);
    print(next);
    print(doubled);
    print(positive);
}
```

Output: `22, 42, true`. [Complete package](examples/features/tuples/).

<a id="methods"></a>

#### Structs, constants and receiver modes

Receiver signatures determine whether a method borrows, mutably borrows or consumes its receiver. Associated constants use `Type::NAME`.

<!-- example: methods -->
```rust
struct Counter {
    value: i64
}

impl Counter {
    const STEP: i64 = 1;

    fn increment(&mut self) {
        let value = &mut (*self).value;
        *value += Counter::STEP;
    }

    fn finish(self: Counter) -> i64 {
        self.value
    }
}

fn main() {
    let mut counter = Counter { value: 41 };
    counter.increment();
    print(counter.finish());
}
```

Output: `42`. [Complete package](examples/features/methods/).

<a id="enums"></a>

#### Enums and pattern matching

Variants can carry named or positional payloads. `if let` tests one enum pattern;
`match` handles all variants. An enum copies implicitly when every variant is
empty or contains only primitive fields. Such enums support `==` and `!=`:
the variant and its active fields are compared. Other enums keep their move
and borrowing rules.

<!-- example: enums -->
```rust
enum Reading {
    Value(i64),
    Missing
}

fn main() {
    let reading = Reading::Value(42);
    let saved = reading;
    print(reading == saved);

    if let Reading::Value(value) = reading {
        print(value);
    } else {
        print(0);
    }

    match saved {
        Reading::Value(value) => { print(value); },
        Reading::Missing => { print(0); },
    }
}
```

Output: `true`, `42`, `42`. [Complete package](examples/features/enums/).

<a id="errors"></a>

#### Result, Option and early propagation

`?` returns the failure/absence from the enclosing function. Result errors of different types require a statically resolved `Outer::from(Inner) -> Outer`; there is no implicit arbitrary conversion.

<!-- example: errors -->
```rust
fn checked(value: i64) -> Result<i64, bool> {
    if value < 0 { return Err(false); }
    Ok(value)
}

fn calculate() -> Result<i64, bool> {
    let value = checked(21)?;
    Ok(value * 2)
}

fn main() {
    match calculate() {
        Ok(value) => { print(value); },
        Err(error) => { print(error); },
    }
}
```

Output: `42`. [Complete package](examples/features/errors/).


### Memory and lifetimes

<a id="moves"></a>

<a id="moves-and-explicit-copies"></a>

#### Moves and primitive copies

Primitive values copy implicitly in assignments, arguments and returns: the source remains available. `copy(x)` remains valid but optional for these values. Enums with only empty or primitive-payload variants copy too. Other non-primitive values retain their move rules, including structs containing only primitive fields. A move transfers cleanup responsibility; it does not request that an allocation be relocated.

<!-- example: moves -->
```rust
struct Message {
    value: i64
}

fn consume(message: Message) {
    print(message.value);
}

fn main() {
    let original: i64 = 21;
    let duplicate = original;
    print(original + duplicate);
    let message = Message { value: 7 };
    let received = message;
    consume(received);
}
```

Output: `42, 7`. [Complete package](examples/features/moves/).

<a id="borrows"></a>

#### Shared borrows and mutable reborrows

References do not transfer cleanup responsibility. `&mut T` grants permission to mutate, not uniqueness: multiple mutable references may coexist. Shared accesses across threads must satisfy the same-lock synchronization requirements, and each target must remain valid through the relevant branch completion points and any surviving borrowed results. Corboc rejects missing proofs. See [mutable access](docs/MUTABLE_ACCESS.md).

Lock facts come from contracts, not type names. A struct marked `#(lock)` gives
its public instance methods the `#(lock: on=self)` contract. Private helpers and
associated constructors do not inherit acquisition. Corboc rejects checked
same-object re-entry through method or helper calls. The developer supplies the
actual locking implementation; the annotation generates no locking code. See
[MT9–MT11](docs/ASYNC_MULTITHREAD_RULES.md).

Types can move to another thread by default. `#(thread: transfer=false)` on a
struct or enum forbids that crossing and propagates through owned fields,
closure captures and retained async state. Moves within the same thread remain
valid. Lifetime and synchronization checks remain separate. See
[thread transfer eligibility](docs/THREAD_TRANSFER.md).

<!-- example: borrows -->
```rust
fn increment(value: &mut i64) {
    *value += 1;
}

fn show(value: &i64) {
    print(*value);
}

fn main() {
    let mut number: i64 = 41;
    increment(&mut number);
    show(&number);
    number += 1;
    print(number);
}
```

Output: `42, 43`. [Complete package](examples/features/borrows/).

<a id="arrays"></a>

#### Universal borrows and for loops

`ref()` and `mut_ref()` are available on every type as exact spellings of `&`
and `&mut`. They borrow the selected place; an existing reference is not
implicitly dereferenced. Mutation permission must already exist.

```rust
fn main() {
    let mut values = [10, 20, 30];

    for value in values.mut_ref() {
        *value += 1;
    }

    for value in values.ref() {
        print(*value);
    }
}
```

The source is evaluated once. Borrowed arrays and slices yield references;
iterator objects yield the payload of `next() -> Option<T>`. Each iteration
has its own scope, with ordinary move, borrowing and cleanup behavior.

#### Fixed arrays, structural repetition and slices

An array carries its element count in its type. A borrowed slice carries an address and length. Repetition evaluates the initializer once and requires a structurally replicable value; slices retain bounds and lifetime checks.

<!-- example: arrays -->
```rust
struct Token {
    kind: u8
}

fn sum(values: &[i64]) -> i64 {
    let mut index: usize = 0;
    let mut result: i64 = 0;
    while index < values.len() {
        result += values[index];
        index += 1;
    }
    result
}

fn main() {
    let mut values: [i64; 3] = [10, 20, 30];
    values[1] = 2;
    let middle = &mut values[1];
    *middle += 1;
    print(sum(&values[..]));

    let tokens: [Token; 2] = [Token { kind: 7 }; 2];
    print(tokens[1].kind);
}
```

Output: `43, 7`. [Complete package](examples/features/arrays/).

<a id="pools"></a>

#### Fixed-capacity pools and allocation handles

`Pool<T>::new(n)` reserves fixed slots. `new` returns `A<T>`; the pool must outlive that allocation. Dropping a live allocation releases its slot after cleanup.

<!-- example: pools -->
```rust
fn main() {
    let mut numbers = Pool<i64>::new(2);
    let first: A<i64> = numbers.new(10);
    let second = numbers.new(20);
    print(*first);
    drop(first);
    let third = numbers.new(30);
    print(*second);
    print(*third);
}
```

Output: `10, 20, 30`. [Complete package](examples/features/pools/).

##### Recoverable pool allocation

`Pool<T>::new(capacity)` creates a fixed-capacity pool. Allocate with `new` to
stop on exhaustion, or `try` to handle it explicitly:

```rust
use std::{Pool, PoolError};

fn main() {
    let mut numbers = Pool<i64>::new(1);
    let first = numbers.new(42);

    match numbers.try(7) {
        Ok(number) => { print(*number); },
        Err(error) => {
            match error {
                PoolError.Full => { print(0); },
            }
        },
    }

    print(*first);
}
```

The argument moves even when `try` returns an error; a failed attempt destroys
the supplied value. See the [pool API](docs/COLLECTIONS_API.md).

<a id="placement"></a>

#### Receivers and placement across scopes

A block result has an explicit receiver. The post-AST placement plan follows transfers to their final destination while keeping allocation addresses stable.

<!-- example: placement -->
```rust
fn main() {
    let mut numbers = Pool<i64>::new(1);
    let received = {
        let local = numbers.new(42);
        local
    };
    print(*received);
}
```

Output: `42`. [Complete package](examples/features/placement/).

<a id="destruction"></a>

#### Destruction before storage release

`drop(value)` and scope exit call `drop(&mut self)` once, before field cleanup. Moving the value changes who performs that cleanup. Types without a custom destructor use the default empty destructor.

<!-- example: destruction -->
```rust
struct Item {
    number: i64
}

impl Item {
    fn drop(&mut self) {
        print((*self).number);
    }
}

fn main() {
    let first = Item { number: 7 };
    let received = first;
    print(1);
    drop(received);
    {
        let scoped = Item { number: 9 };
    }
}
```

Output: `1, 7, 9`. [Complete package](examples/features/destruction/).

<a id="regions"></a>

#### Datastack budgets, local regions and page reclamation

The global datastack annotation and its properties are optional. `stack_region` supplies a local growing-data budget. `free_pages` requests OS reclamation of complete unused pages after cleanup, distinct from moving a cursor.

<!-- example: regions -->
```rust
#(datastack: size=4M, region_stack_size=4M, region_size=64K)
use std::Vector;

fn main() {
    let mut vectors = Pool<Vector<i64>>::new(1);
    #(stack_region: max_size=64K, count=1) #(free_pages) {
        let mut values = vectors.new();
        let mut number: i64 = 0;
        while number < 3 {
            values.push(number);
            number += 1;
        }
        print(values.len());
    }
}
```

Output: `3`. [Complete package](examples/features/regions/).


### Collections and pipelines

<a id="vector"></a>

#### Vectors and extraction

The vector descriptor has fixed size; its contiguous payload grows within its region budget. Insertion moves an item into the vector. Extraction transfers it to the receiver.

<!-- example: vector -->
```rust
use std::Vector;

fn main() {
    let mut vectors = Pool<Vector<i64>>::new(1);
    let mut values = vectors.new();
    values.push(10);
    values.push(20);
    print(values[0]);
    match values.pop() {
        Some(value) => { print(value); },
        None => { print(0); },
    }
    print(values.len());
}
```

Output: `10, 20, 1`. [Complete package](examples/features/vector/).

<a id="map"></a>

#### HashMap lookup, replacement and removal

Maps accept integer and boolean keys. Insertion moves its key and value; lookup borrows its key. Remaining values are destroyed with the map, while an extracted value belongs to its receiver.

<!-- example: map -->
```rust
use std::HashMap;

fn main() {
    let mut values = HashMap<i64, i64>::new();
    let key: i64 = 7;
    let _previous = values.insert(key, 42);
    match values.get(&key) {
        Some(value) => { print(*value); },
        None => { print(0); },
    }
    match values.remove(&key) {
        Some(value) => { print(value); },
        None => { print(0); },
    }
}
```

Output: `42, 42`. [Complete package](examples/features/map/).

<a id="text"></a>

#### UTF-8 text and caller-owned bytes

`String` owns region-backed UTF-8 bytes; a literal provides a static `&str` view. Byte length differs from character count. Convert to a byte slice explicitly with `as_bytes()`. Both `String` and `&str` provide `split(separator)`: its iterator yields borrowed `&str` pieces, preserving empty pieces without allocating strings.

`String<N>` instead keeps at most `N` UTF-8 bytes inline, with its bound known
at compilation. Oversized construction or replacement returns an error without
truncation. See [bounded string APIs](docs/UTF8_STRINGS.md#bounded-inline-utf-8-strings).

<!-- example: text -->
```rust
use std::String;

fn main() {
    let mut strings = Pool<String>::new(1);
    let mut text = strings.new();
    text.push_str("été,soleil,");
    print(text.byte_len());

    let literal = "ok";
    let bytes = literal.as_bytes();
    print(bytes.len());

    // Each item is a borrowed &str; no String is allocated for a piece.
    let mut pieces = text.split(",");
    loop {
        match pieces.next() {
            Some(piece) => { print(piece.byte_len()); },
            None => { break; },
        }
    }
}
```

Output: `13, 2, 5, 6, 0`. [Complete package](examples/features/text/).

<a id="bounded-text"></a>

#### Inline UTF-8 strings with a compile-time byte maximum

String<N> keeps UTF-8 bytes inline; exceeding the bound returns an error before changing the string.

<!-- example: bounded_text -->
```rust
use std::String;

fn main() {
    // Two UTF-8 characters occupy four bytes, exactly our inline budget.
    let mut name = match String<4>::try_from("éé") {
        Ok(value) => { value },
        Err(_error) => { return; },
    };

    print(name.capacity());
    print(name.len());

    // Five bytes cannot fit. The previous content stays intact.
    match name.set("hello") {
        Ok(()) => { print(false); },
        Err(_error) => { print(true); },
    }

    print(name.len());
}
```

Output: `4, 4, true, 4`. [Complete package](examples/features/bounded_text/).

<a id="closures"></a>

#### Closures and explicit callable passing

A closure is a concrete captured object. Parameters are typed and braces are required. `fn(...) -> R`, `&fn(...) -> R` and `&mut fn(...) -> R` distinguish value passing from borrowing. Without `move`, primitive/shared-reference captures copy at creation. Explicit `move` transfers captured bindings; references retain their target dependencies.

<!-- example: closures -->
```rust
fn apply(f: fn(i64) -> i64, value: i64) -> i64 {
    f(value)
}

fn inspect(f: &fn(i64) -> i64, value: i64) -> i64 {
    f(value)
}

fn advance(f: &mut fn() -> i64) -> i64 {
    f()
}

fn main() {
    let offset: i64 = 2;
    let c = |value: i64| { value + offset };

    print(c(40));
    print(inspect(&c, 8));
    print(apply(c, 18));
    print(offset);

    let mut count: i64 = 0;
    let mut next = move || {
        count += 1;
        count
    };

    print(advance(&mut next));
    print(next());
}
```

Output: `42, 10, 20, 2, 1, 2`. [Complete package](examples/features/closures/).

<a id="iter"></a>

#### STD iterator pipelines

Only `Iter` borrows the source. Each adapter owns the preceding stage. `collect(&mut destination)` consumes the chain and moves its outputs into caller-selected storage.

<!-- example: iter -->
```rust
use std::iter::iter;

struct Counter {
    position: i64,
    end: i64
}

impl Counter {
    fn next(&mut self) -> Option<i64> {
        let value = (*self).position;
        if copy(value) >= (*self).end { return None; }
        let position = &mut (*self).position;
        *position = copy(value) + 1;
        Some(value)
    }
}

fn main() {
    let mut counter = Counter { position: 1, end: 7 };
    let mut storage = Pool<Vector<i64>>::new(1);
    let mut destination = storage.new();
    iter(&mut counter)
        .filter(|item: &i64| { *item % 2 == 0 })
        .map(|item: i64| { item * 10 })
        .reduce(|acc: i64, item: i64| { acc + item })
        .collect(&mut destination);
    print(destination.len());
    print(destination[0]);
    print(counter.position);
}
```

Output: `1, 120, 7`. [Complete package](examples/features/iter/).


### Generic code and packages

<a id="generic"></a>

#### Contracts on generic structs

Type parameters and their constraints also apply to structs. Concrete instantiation retains the ordinary ownership and borrowing obligations of its fields.

<!-- example: generic -->
```rust
#(type: T)
pub struct Holder<T> {
    value: T
}

fn main() {
    let holder: Holder<i64> = Holder { value: 42 };
    print(holder.value);
}
```

Output: `42`. [Complete package](examples/features/generic/).

<a id="contracts"></a>

#### Static structural type contracts

A `with` contract requires the listed methods and permits additional ones. The compiler resolves the concrete implementation statically; no trait object or dynamic dispatch is introduced.

<!-- example: contracts -->
```rust
#(type: V)
struct Boxed<V> {
    value: V
}

impl Boxed<V> {
    fn new(value: V) -> Boxed<V> {
        Boxed { value: value }
    }

    fn get(&self) -> V {
        (*self).value
    }
}

#(type: V)
#(type: S<V> with {
    fn get(&self) -> V;
})
struct Reader<S, V> {
    source: S
}

impl Reader<S, V> {
    fn new(source: S) -> Reader<S, V> {
        Reader { source: source }
    }

    fn get(&self) -> V {
        let source = &(*self).source;
        source.get()
    }
}

fn main() {
    let reader = Reader::new(Boxed::new(42));
    print(reader.get());
}
```

Output: `42`. [Complete package](examples/features/contracts/).

<a id="modules"></a>

#### Packages, modules, visibility and aliases

A package is named in `package.toml`. Files under `src` provide components. `pub`, grouped `use` and `as` control access and local names; dependencies can be pinned through package metadata.

<!-- example: modules -->
```rust
use feature_demo::math::{answer as result, twice};

fn main() {
    print(result());
    print(twice(21));
}
```

Output: `42, 42`. [Complete package](examples/features/modules/).

The imported component is `src/math/numbers.crb`:

<!-- example-file: modules/src/math/numbers.crb -->
```rust
pub fn answer() -> i64 {
    42
}

pub fn twice(value: i64) -> i64 {
    value * 2
}
```

The directory contributes `math` to the import path; the component file declares
its public functions. [Module and dependency guide](docs/MODULES.md) covers
`path`, Git dependencies and immutable revisions.

<a id="target"></a>

#### Conditional compilation

Target selection happens before import resolution. Excluded branches cannot introduce unavailable imports or collisions. The paired `endif` ends selection; it does not create a runtime scope.

<!-- example: target -->
```rust
#(if: target.family == "unix")
fn answer() -> i64 {
    42
}

#(endif)
#(if: target.family == "windows")
fn answer() -> i64 {
    42
}

#(endif)
fn main() {
    print(answer());
}
```

Output: `42`. [Complete package](examples/features/target/).


### Async and threads

<a id="async"></a>

#### Futures, suspension and execution branches

Calling an async function creates an inactive Future and captures its arguments immediately. `yield;` suspends cooperatively; `.await` waits without blocking a poll worker. Synchronous `main` starts an execution and waits through its handle.

<!-- example: async -->
```rust
async fn twice(value: i64) -> i64 {
    yield;
    value * 2
}

async fn calculate() -> i64 {
    twice(21).await
}

fn main() {
    let execution = runtime::spawn(calculate());
    match execution.join() {
        Ok(value) => { print(value); },
        Err(_error) => { print(0); },
    }
}
```

Output: `42`. [Complete package](examples/features/async/).

<a id="threads"></a>

#### Native threads and captured loans

A native execution receives its block captures. The target of a captured reference must remain valid through its use; this example joins before accessing the target again.

<!-- example: threads -->
```rust
fn main() {
    let mut number: i64 = 41;
    let view = &mut number;
    let execution = runtime::thread({
        move view;
        *view += 1;
    });
    match execution.join() {
        Ok(()) => { print(number); },
        Err(_error) => { print(0); },
    }
}
```

Output: `42`. [Complete package](examples/features/threads/).

<a id="blocking"></a>

#### Blocking work from an async context

`spawn_blocking` returns an `AsyncHandle`, awaited inside async code. Blocking `join()` belongs in a synchronous context. The blocking operation runs on a dedicated worker.

<!-- example: blocking -->
```rust
async fn operation() -> i64 {
    42
}

async fn calculate() -> i64 {
    let execution = runtime::spawn_blocking(operation());
    match execution.await {
        Ok(value) => { value },
        Err(_error) => { 0 },
    }
}

fn main() {
    let execution = runtime::spawn(calculate());
    match execution.join() {
        Ok(value) => { print(value); },
        Err(_error) => { print(0); },
    }
}
```

Output: `42`. [Complete package](examples/features/blocking/).


### STD in practice

<a id="async-file"></a>

#### Async files by default

`std::io::asyn::File` awaits its operations. Modes, permissions and seek origins are shared with `std::io::File`. An inner block closes the file before path deletion; error values are also cleaned up automatically at scope exit.

<!-- example: async_file -->
File paths are UTF-8 `&str` values without a trailing NUL. Mode flags combine:

```rust
File::open("journal.wal", FileMode::READ | FileMode::WRITE | FileMode::CREATE)
```

```rust
use std::io::{FileMode, FilePerm, SeekFrom};
use std::io::asyn::{File, FileError};

async fn round_trip() -> Result<usize, FileError> {
    let path = "demo.bin";
    let count = {
        let mut file = File::create(
            &path[..], FileMode::READ_WRITE | FileMode::TRUNCATE, FilePerm.DefaultMode
        ).await?;

        let bytes: [u8; 2] = [111, 107];
        file.write(&bytes[..]).await?;
        file.seek(SeekFrom.Start(0)).await?;

        let mut output: [u8; 2] = [0; 2];
        file.read(&mut output[..]).await?
    }; // The file is closed when this block ends.

    File::delete(&path[..]).await?;
    Ok(count)
}

fn main() {
    let execution = runtime::spawn(round_trip());
    match execution.join() {
        Ok(result) => {
            match result {
                Ok(count) => { print(count); },
                Err(_error) => { print(0); },
            }
        },
        Err(_error) => { print(-1); },
    }
}
```

Output: `2`. [Complete package](examples/features/async_file/).

<a id="file"></a>

#### Blocking files, errors and caller-provided buffers

The caller chooses open mode, permissions and buffer size. Paths in this API are NUL-terminated byte slices. This program creates a file in its working directory, performs I/O and deletes it. Moving or dropping `File` closes its native handle once.

<!-- example: file -->
```rust
use std::io::{File, FileError};
use std::io::{FileMode, FilePerm, SeekFrom};

fn run() -> Result<usize, FileError> {
    let path = "demo.bin";
    let count = {
        let mut file = File::create(&path[..], FileMode::READ_WRITE | FileMode::TRUNCATE, FilePerm.DefaultMode)?;
        let bytes: [u8; 2] = [111, 107];
        file.write(&bytes[..])?;
        file.seek(SeekFrom.Start(0))?;
        let mut output: [u8; 2] = [0; 2];
        file.read(&mut output[..])?
    }; // The file is closed when this block ends.

    File::delete(&path[..])?;
    Ok(count)
}

fn main() {
    match run() {
        Ok(count) => { print(count); },
        Err(_error) => { print(0); },
    }
}
```

Output: `2`. [Complete package](examples/features/file/).

<a id="buffered"></a>

#### Buffered I/O through structural contracts

Buffered wrappers borrow the stream and scratch buffer explicitly. Call `flush()` to send pending bytes; destruction discards pending output. This example creates a local file and deletes it after closing it.

<!-- example: buffered -->
```rust
use std::io::File;
use std::io::{FileMode, FilePerm};
use std::io::buffered::BufWriter;

fn main() {
    let path = "demo.bin";
    {
        let mut file = match File::create(&path[..], FileMode::READ_WRITE | FileMode::TRUNCATE, FilePerm.DefaultMode) {
            Ok(file) => { file },
            Err(_error) => { return; },
        };
        let mut scratch: [u8; 4] = [0; 4];
        {
            let mut writer = BufWriter::new(&mut file, &mut scratch[..]);
            let bytes: [u8; 2] = [111, 107];
            match writer.write(&bytes[..]) {
                Ok(count) => { print(count); },
                Err(_error) => { return; },
            }
            match writer.flush() {
                Ok(()) => {},
                Err(_error) => { return; },
            }
        }
        match file.stats() {
            Ok(stats) => { print(stats.size()); },
            Err(_error) => { return; },
        };
    } // The writer is flushed, then the file closes at scope exit.

    match File::delete(&path[..]) {
        Ok(()) => {},
        Err(_error) => { print(0); },
    }
}
```

Output: `2, 2`. [Complete package](examples/features/buffered/).

<a id="network"></a>

#### Typed network endpoints and datagrams

IPv4 address objects are passed to bind/connect. Port zero asks the OS for a local port. This loopback UDP exchange uses caller-provided buffers and no external server; TCP and async APIs are linked below.

<!-- example: network -->
```rust
use std::net::ipv4::{Addr, SocketAddr};
use std::net::udp::{Listener, connect};
use std::net::SocketError;

fn exchange() -> Result<usize, SocketError> {
    let mut listener = Listener::bind(SocketAddr::new(Addr::new(127, 0, 0, 1), 0))?;
    let mut peer = connect(listener.addr())?;
    let input: [u8; 1] = [42];
    peer.send(&input[..])?;
    let mut output: [u8; 1] = [0];
    let datagram = listener.recv(&mut output[..])?;
    print(output[0]);
    Ok(datagram.count())
}

fn main() {
    match exchange() {
        Ok(count) => { print(count); },
        Err(_error) => { print(0); },
    }
}
```

Output: `42, 1`. [Complete package](examples/features/network/).

<a id="encoding"></a>

#### Hashes and encodings with bounded output

The STD has native hashing, crypto, TLS, codecs and platform I/O. APIs that produce variable-length bytes take caller-owned buffers. This example hashes two bytes and hex-encodes the fixed digest without an unbounded allocation.

<!-- example: encoding -->
```rust
use std::crypto::sha256::Sha256;
use std::encoding::hex::encode;

fn main() {
    let input: [u8; 2] = [111, 107];
    let mut hash = Sha256::new();
    match hash.update(&input[..]) {
        Ok(()) => {},
        Err(_error) => { return; },
    }
    let digest = hash.finish();
    let mut encoded: [u8; 64] = [0; 64];
    match encode(&digest[..], &mut encoded[..]) {
        Ok(count) => { print(count); },
        Err(_error) => { print(0); },
    }
}
```

Output: `64`. [Complete package](examples/features/encoding/).

<a id="binary"></a>

#### Binary primitives with explicit endianness

The caller provides storage and chooses byte order for every multi-byte read or write.

<!-- example: binary -->
```rust
use std::encoding::binary::{write_u32_be, read_u32_be, read_u32_le, Error};

fn encode() -> Result<(), Error> {
    let mut bytes: [u8; 4] = [0; 4];

    // 0x01020304 becomes the four bytes 01 02 03 04.
    let written = write_u32_be(16909060, &mut bytes[..])?;
    print(written);

    let big = read_u32_be(&bytes[..])?;
    let little = read_u32_le(&bytes[..])?;
    print(big);
    print(little);

    Ok(())
}

fn main() {
    match encode() {
        Ok(()) => {},
        Err(_error) => { },
    }
}
```

Output: `4, 16909060, 67305985`. [Complete package](examples/features/binary/).

<a id="time"></a>

#### Monotonic time and blocking deadlines

Duration expresses a span; Instant reads a monotonic clock, and Timer waits for a deadline.

<!-- example: time -->
```rust
use std::time::{Duration, Instant, Error};
use std::time::{Timer, sleep};

fn wait() -> Result<(), Error> {
    let start = Instant::now()?;
    sleep(Duration::from_millis(2))?;

    let elapsed = start.elapsed()?;
    print(elapsed.as_nanos() >= 2000000);

    // A zero-duration deadline is already ready when waited.
    let timer = Timer::after(Duration::from_nanos(0))?;
    timer.wait()?;

    Ok(())
}

fn main() {
    match wait() {
        Ok(()) => { print(1); },
        Err(_error) => { },
    }
}
```

Output: `true, 1`. [Complete package](examples/features/time/).

<a id="async-time"></a>

#### Async deadline waits

Async waits suspend the caller task while an existing blocking worker performs the native wait.

<!-- example: async_time -->
```rust
use std::time::{Duration, Error};
use std::time::asyn::{sleep, Timer};

async fn delayed_value() -> Result<i64, Error> {
    sleep(Duration::from_millis(2)).await?;

    let timer = Timer::after(Duration::from_nanos(0))?;
    timer.wait().await?;

    Ok(42)
}

fn main() {
    let execution = runtime::spawn(delayed_value());

    // Launch failures and the task's own errors remain distinct.
    match execution.join() {
        Ok(result) => {
            match result {
                Ok(value) => { print(value); },
                Err(_error) => { },
            }
        },
        Err(_error) => { },
    }
}
```

Output: `42`. [Complete package](examples/features/async_time/).

<a id="compression"></a>

#### Compression with an explicit workspace

Compression APIs borrow caller-owned input, output and workspace. The example provides the documented Gzip level-1–9 workspace, round-trips a frame and checks its decoded size through the returned count.

<!-- example: compression -->
```rust
use std::compression::gzip::{Params, compress, decompress};

fn main() {
    let input: [u8; 3] = [65; 3];
    let mut encoded: [u8; 128] = [0; 128];
    let mut workspace: [u64; 36864] = [0; 36864];
    let params = Params::new();
    let count = match compress(&input[..], &mut encoded[..], &params, &mut workspace[..]) {
        Ok(count) => { count },
        Err(_error) => { return; },
    };
    let mut output: [u8; 3] = [0; 3];
    match decompress(&encoded[..count], &mut output[..]) {
        Ok(count) => { print(count); },
        Err(_error) => { return; },
    }
    print(output[0]);
}
```

Output: `3, 65`. [Complete package](examples/features/compression/).


### Native interop

<a id="foreign"></a>

#### Unchecked C, typed operands and native assembly

Foreign code belongs inside `@unchecked`. `${name}` binds an existing Corbo operand. Header paths are explicit. `addr` is restricted to the unchecked block, and its address must not escape it. ABI, lifetime and memory correctness inside foreign code remain the developer’s responsibility.

<!-- example: foreign -->
```rust
fn main() {
    let mut answer: i64 = 0;
    @unchecked {
        @c(includes={"stdint.h"}) {
            ${answer} = (int64_t)42;
        }
        @asm { nop }
    }
    print(answer);
}
```

Output: `42`. [Complete package](examples/features/foreign/).

[Foreign-code contracts](docs/FOREIGN_C.md) explain paired target selection,
header paths, typed operands and unchecked responsibilities.

#### Bounded channels

The borrowed channel must survive both tasks. Capacity is explicit; async waiting suspends a task when the queue is full or empty.

<!-- example: channels -->
```rust
use std::sync::asyn::channel::Channel;

async fn produce(channel: &Channel<i64>) {
    drop(channel.send(10).await);
    drop(channel.send(20).await);
    channel.close();
}

async fn consume(channel: &Channel<i64>) -> i64 {
    let mut total: i64 = 0;

    loop {
        let received = channel.recv().await;

        match received {
            Some(value) => { total += value; },
            None => { break; },
        }
    }

    total
}

fn main() {
    // Only one value can wait in this queue; the producer suspends when full.
    let channel = Channel<i64>::new(1);
    let reader = runtime::spawn(consume(&channel));
    let writer = runtime::spawn(produce(&channel));

    drop(writer.join());

    match reader.join() {
        Ok(total) => { print(total); },
        Err(_error) => {},
    }
    // The channel is destroyed automatically after both borrowed users finish.
}
```

Output: `30`. [API](docs/CHANNELS.md).


## Explore the STD

Import the native collection types with `use std::{Vector, HashMap, String};`.
Their public names live in [collections.crb](stdlib/src/collections.crb). Native
collection algorithms live in the runtime; bounded `String<N>` is implemented
in the STD. See the [collection API guide](docs/COLLECTIONS_API.md)
for construction, element ownership, borrowing and cleanup.

### Mutex guards and shared acquisition

Both variants acquire through `&self`. A guard unlocks automatically at scope
exit; the async guard below remains valid across `yield`.

<!-- example: mutex -->
```rust
use std::sync::Mutex;
use std::sync::asyn::Mutex as AsyncMutex;

async fn async_value() -> i64 {
    let mutex = AsyncMutex::new(10);
    {
        let mut guard = mutex.lock().await;
        let target = guard.get_mut();
        *target = 42;
        yield;
    }
    let guard = mutex.lock().await;
    let view = guard.get();
    *view
}

fn main() {
    let mutex = Mutex::new(10);
    {
        let guard = mutex.lock();
        let mut moved = guard;
        let target = moved.get_mut();
        *target = 42;
    }
    {
        let guard = mutex.lock();
        let view = guard.get();
        print(*view);
    }
    let execution = runtime::spawn(async_value());
    match execution.join() {
        Ok(value) => { print(value); },
        Err(_) => { print(-1); },
    }
}
```

Output: `42, 42`. [Complete package](examples/features/mutex/).

### Synchronous defaults and explicit async APIs

Synchronous APIs use their ordinary package path. Import an `asyn` namespace
when the operation should suspend an async task:

```rust
use std::io::File;                    // File::open(...)
use std::io::asyn::File as AsyncFile; // AsyncFile::open(...).await

use std::net::tcp;                    // tcp::connect(...)
use std::net::asyn::tcp as async_tcp; // async_tcp::connect(...).await

use std::time::sleep;                 // sleep(...)
use std::time::asyn::sleep as async_sleep;
```

`main` is synchronous; `.await` requires an async body. Modes and permissions
stay in `std::io`, addresses in `std::net::ipv4`, and Duration/Instant in
`std::time`. Async files and timers use blocking workers. TCP and UDP async
operations use the readiness reactor. TLS is currently synchronous under
`std::net::tls`.

`std::sync::Mutex<T>` blocks the calling thread. `std::sync::asyn::Mutex<T>` parks a waiting
task; its guard can survive suspension and resume on another worker. Both
expose `new(value)`, `lock(&self)`, and guard `get()` / `get_mut()` methods.
A guard releases its lock at scope exit. Synchronous guards are marked
`#(thread: transfer=false)`; async guards are transferable. These ordinary STD
types use the same lock contracts as user-defined locks.

| Package | Main capabilities | Reference |
| --- | --- | --- |
| `std::{Pool, Vector, HashMap, String}` | Fixed-capacity pools, vectors, maps, growing UTF-8 strings and inline `String<N>` with a compile-time byte maximum | [Collections](docs/COLLECTIONS_API.md) · [Bounded strings](docs/UTF8_STRINGS.md#bounded-inline-utf-8-strings) |
| `std::iter` | Iter, Map, Filter, Reduce and instance `collect` | [API](docs/STDLIB.md#stditer) |
| `std::sync::Mutex`, `std::sync::asyn::Mutex` | Shared-reference acquisition, scope-owned guards and task-parking async waits | [API](docs/ASYNC_API.md#mutex-ownership) |
| `std::sync::channel`, `std::sync::asyn::channel` | Bounded FIFO channels, owned messages and task-parking async waits | [API](docs/CHANNELS.md) |
| `std::io`, `std::io::asyn` | File read/write, cursor-preserving read_at/write_at, seek, stats, rename/delete and buffered streams | [API](docs/STDLIB.md#stdio) · [File guide](docs/FILE.md) |
| `std::net::{tcp, udp}`, `std::net::asyn::{tcp, udp}` | Typed IPv4 endpoints, sockets, partial TCP I/O and borrowed async halves | [Networking](docs/NETWORKING.md) |
| `std::net::http` | Request/response head parsing, configurable static limits and optional streaming bodies through a reader contract | [HTTP](docs/HTTP.md) |
| `std::net::tls` | Native TLS 1.3 key schedule, records, handshake and X.509 validation; optional OpenSSL wrapper | [API](docs/STDLIB.md#stdnettls) |
| `std::crypto` | AES-GCM/CBC, SHA families, HMAC/HKDF, Argon2id, random, P-256 and key containers | [API](docs/STDLIB.md#stdcryptoaes) |
| `std::encoding` | Hex, Base64, DER and PEM with caller-owned output | [API](docs/STDLIB.md#stdencodinghex) |
| `std::encoding::binary` | Primitive reads/writes with explicit little-/big-endian byte order and caller-provided buffers | [Binary API](docs/BINARY_AND_TIME_API.md#stdencodingbinary) |
| `std::time`, `std::time::asyn` | Monotonic Duration/Instant, sleep and reusable deadline timers; async waits use blocking workers | [Time API](docs/BINARY_AND_TIME_API.md) |
| `std::compression::{gzip, zstd}` | Native bounded codecs, streaming and dictionary support | [Compression](docs/COMPRESSION.md) |
| `runtime::metrics` | Atomic reserved, committed and occupied datastack/region byte counters | [Metrics](docs/RUNTIME_METRICS.md) |
| `std::env` | Process arguments while keeping `main` argument-free | [API](docs/STDLIB.md#stdenv) |

The API reference documents the actual supported cryptographic profiles and
error contracts. RSA key parsing/serialization does not imply RSA signing or
encryption support. API availability is not a claim of an independent security audit.

## Source layout and runtime boundary

| Location | Responsibility |
| --- | --- |
| [omework/corboc](https://github.com/omework/corboc) | Active self-hosted lexer, parser, representations, verifier, placement and C11 backend |
| [stdlib/src](stdlib/src/) | STD APIs and their portable/platform-specific implementations |
| [runtime/corbo](runtime/corbo/README.md) | Runtime allocation, collection, cleanup, scheduling and reactor algorithms in Corbo |
| [runtime](runtime/README.md) | Canonical C ABI and retained C comparison implementation |
| [ide](ide/README.md) | Vim/Neovim and VS Code support for `.crb` |
| [rust_frontend](rust_frontend/README.md) / [prototype](prototype/README.md) | Frozen/historical reference implementations |

`corboc` pins STD/runtime inputs with `corbo.lock`. The current backend generates
C11. Runtime machine/ABI primitives retain explicit `@unchecked`/`@c` bindings;
the algorithm port does not make the toolchain C-free. The shared memory library
is also available to C through [corbo_runtime.h](runtime/corbo_runtime.h).

The [runtime cycle report](docs/cycles/CORBO_RUNTIME_CYCLE.md) records differential
C/Corbo execution and self-reconstruction evidence, including platform limits.

## Build the compiler from source

The active self-hosted compiler is maintained in
[omework/corboc](https://github.com/omework/corboc). This language repository owns
the grammar, rules, STD, runtime, examples and editor support. The compiler's
`corbo.lock` pins its exact STD/runtime revision.

Starting from this language checkout, clone the compiler beside it and provide
an existing compatible seed:

```sh
CORBO_LANGUAGE_ROOT="$PWD"
git clone git@github.com:omework/corboc.git ../corboc
cd ../corboc
python3 scripts/corbo_sources.py --from-repo "$CORBO_LANGUAGE_ROOT"
python3 scripts/build.py --seed /absolute/path/to/corboc --verify-self
export PATH="$PWD/build/install/bin:$PATH"
cd "$CORBO_LANGUAGE_ROOT"
```

`--from-repo` supplies Git objects at the locked commit rather than copying
uncommitted files. Omit it to fetch the pinned source from GitHub. The
[compiler build guide](https://github.com/omework/corboc#build-and-self-rebuild)
details seed requirements, prerequisites and installation options.

From the compiler repository, rebuild the compiler through its normal command:

```sh
corboc build . -o build/install/bin/corboc-next
```

The frozen [Rust reference](rust_frontend/README.md) retains older syntax and
cannot bootstrap the current compiler. Historical Din/Crust packages need `.crb`
source filenames, an entry point at `src/main.crb` and the matching installed STD.

## Documentation and validation status

Corbo is experimental. The grammar, accepted rules, implemented paths and
executed validation are separate sources of information. This README's runnable
examples demonstrate their particular paths; they are not a proof that every
composition is implemented or memory-safe.

General callable calls and explicit callable passing execute independently of
iterator adapters. All ten forms rejected during the original documentation
exercise are now supported, including direct borrowed returns, structural
function contracts, numeric/text operations and branch wrappers. The
[coverage follow-up](docs/cycles/DOCUMENTATION_COVERAGE_CYCLE.md) records the
executed programs, rejection boundaries and platform limits; the
[historical observations](docs/DOCUMENTATION_LIMITS.md) remain available.

Source documentation uses `//!` for modules and `///` for declarations and
members, plus Doxygen-style comments for the C ABI/reference. The coverage check
also checks internal helpers, rather than only public APIs.

```sh
python3 scripts/stdlib_docs.py > docs/STDLIB.md
python3 scripts/stdlib_docs.py --runtime > docs/RUNTIME.md
python3 scripts/stdlib_docs.py --check
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc
```

The last command needs a host C11 compiler and local loopback socket access.
Results and generated programs are retained in `build/documentation/`.
This documentation pass validates execution on the macOS ARM64 host; it does
not repeat the full platform matrix. Windows ARM64 execution remains deferred.

Documentation defaults to English. Historical French counterparts use `-fr.md`.

## Project references

- [Core grammar](CORE_GRAMMAR.ebnf) and [language rules](docs/LANGUAGE_RULES.md)
- [Memory-safety status](docs/SAFETY.md)
- [Representation model](docs/MEMORY_REPRESENTATION.md)
- [Implementation checklist](docs/IMPLEMENTATION_CHECKLIST.md) and [verification matrix](docs/VERIFICATION_MATRIX.md)
- [Validation guidelines](docs/VALIDATION_GUIDELINES.md) and [independent audit guide](docs/CORE_AUDIT_HANDOFF.md)
- [Compiler repository boundary](docs/COMPILER_REPOSITORY.md)

## License

Corbo and its standard library are available under either the [MIT License](LICENSE-MIT)
or the [Apache License, Version 2.0](LICENSE-APACHE), at your option.
Derived portions retain their additional [third-party notices](stdlib/THIRD_PARTY_NOTICES.txt).
