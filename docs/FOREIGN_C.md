# Foreign C regions

`@c { ... }` remains a language form alongside `@c++ { ... }` and `@asm { ... }`.
All three must be enclosed in `@unchecked`. The earlier full rewrite concerned
existing STD/compiler implementation code, not removal of embedded C support.

```rust
@unchecked {
    @c(includes={"stdint.h"}) {
        int64_t value = 20;
        *${number_addr} = value;
    }
}
```

The Rust lexer preserves C text, header tokens and operand source spans without
resolving names, interpreting C statements, or checking unchecked enclosure.
The grammar records the enclosure requirement; parser and later-stage work must
implement their respective responsibilities.

The final backend remains primitive C++. Embedded C integration is intended to
use that generated translation unit; this does not mean every C construct is
valid C++. The supported C subset, incompatible constructs and header/linkage
handling must be established when the backend stage is reviewed. No C semantic
compatibility or end-to-end C compilation is claimed by lexical recognition.

Historical C runtime files remain comparison artifacts; restoring `@c` does not
restore the retired C code-generation backend.
