[Français](DEFINITION_METHODS-fr.md)

# Definition-local methods and explicit receivers

This syntax supersedes the external `impl` examples in historical design and
validation reports. Ownership, borrowing, visibility and destruction rules are
unchanged. The frozen Rust frontend is not the current syntax reference.

Fields and enum variants end with `;`. Fields/variants, associated constants
and methods may be declared in any order. Constructors still use comma-separated field values;
match arms and positional payloads also retain their commas.

```rust
struct Counter {
    value: i64;

    pub const STEP: i64 = 2;

    pub fn new(value: i64) Counter {
        Counter { value: value }
    }

    pub fn increment(&mut self) {
        self.value += Counter::STEP;
    }

    pub fn value(&self) i64 {
        self.value
    }
}

enum Outcome {
    Data(i64);
    End;

    pub fn is_end(&self) bool {
        match self {
            Outcome::Data(value) => { false },
            Outcome::End => { true },
        }
    }
}
```

Return types follow the parameter list directly. Omitting a return type means
unit; `fn reset(&mut self) ()` spells the same result explicitly. Tuple return
values use `fn pair() (i64, bool)`. Callable types and explicit closure result
annotations follow the same convention: `fn(i64) i64` and `|x: i64| i64 { x }`.
Static structural contracts use ordinary method signatures without arrows.

A typed receiver constrains existing parameters of the enclosing type:

```rust
#(type: T)
struct Container<T> {
    value: T;

    pub fn new(value: T) Container<T> {
        Container { value: value }
    }

    pub fn doubled(self: &Container<i64>) i64 {
        self.value * 2
    }
}
```

`doubled` is available on `Container<i64>` and is omitted from other
specializations. Its body is checked with that concrete receiver. The method
introduces no new generic parameter and performs no dynamic dispatch.
`self: &mut Container<i64>` permits mutation; `self: Container<i64>` consumes
the receiver. `&self` and `&mut self` remain shorthand for unconstrained owner
receivers. Receiver types must name the enclosing type. Existing structural
contracts and the prohibition on method/field name collisions still apply.

## Compiler representation and migration

The frontend lowers definition-local methods to its existing method-owner AST
nodes before package linking. Thus scope, dependency and placement analyses use
the same representation. Token-aware normalization preserves constructor syntax,
array lengths, strings, comments and opaque `@c`/`@asm` bodies. Diagnostic source
maps compose through this pass.

Legacy external `impl` blocks and arrow returns remain accepted as bootstrap
compatibility syntax for older seeds and generated specialization recipes. New
STD sources, examples and the reference grammar use definition-local methods
and arrow-free return types. No new runtime mechanism is required.

## Annotations inside definitions

Annotations keep their existing target and meaning inside both struct and enum
bodies. Put them before `pub`/`async` and the declaration they describe:

- `#(type: ...)` constrains a method or associated function; independently generic
  associated functions do not need a `self` parameter.
- `#(branch: ...)` and `#(lock: ...)` describe method effects with the same
  signature checks as ordinary functions.
- `#(configurable)` marks an associated constant. Override it by its qualified
  name (`Settings::LIMIT`); lexical overrides specialize its enclosing type and
  methods, and restore the previous value outside the override block.
- `#(if: ...)` / `#(endif)` select members before name resolution.
- Block annotations (`override`, `stack_region`, `free_pages`) retain their block
  targets inside method bodies. Object annotations (`lock` and `thread`) remain
  before their enclosing type declaration, not before a field or constant.

```rust
struct Settings {
    #(configurable)
    pub const LIMIT: i64 = 4;

    #(type: T)
    pub fn identity(value: T) T {
        value
    }
}

fn main() {
    print(Settings::LIMIT);

    #(override: Settings::LIMIT=8) {
        print(Settings::LIMIT);
        print(Settings::identity(42));
    }

    print(Settings::LIMIT);
}
```

No annotation is silently ignored on an incompatible declaration. Fields and
variants may appear before or after methods and associated constants.

## Associated array bounds

A fixed array length can name a compile-time constant through `Type::NAME` or,
inside its owning type, `Self::NAME`. The same spelling works in repetition
expressions. The compiler resolves the constant before layout and uses the
active lexical configuration when it is marked configurable.

```rust
struct Tracker {
    #(configurable)
    const CONSUMERS: u16 = 5;

    offsets: [usize; Self::CONSUMERS];

    fn new() Tracker {
        Tracker { offsets: [0; Self::CONSUMERS] }
    }
}
```

Unknown constants and runtime values cannot determine fixed array lengths.

`Self` names the enclosing struct or enum in field types, method signatures and
method bodies. It does not require a source-level `impl` block. Outside an
enclosing nominal type it is rejected with an explicit scoped-alias diagnostic.
