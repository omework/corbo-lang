[Français](MODULES-fr.md)

# Packages and modules

A project declares its package name in `package.toml` at its root.
Sources live in `src/`. The executable entry point is a synchronous
`main` in `src/main.crb`. The extension follows the current language name
and may change independently of the import paths.

Every source directory is a module. All source files directly in that
directory contribute to the same module. The directory structure and the
manifest name determine the path. Moving a declaration to another file in
the same directory leaves its path intact.

```toml
[package]
name = "server"
```

A declaration is private to its module by default. `pub` allows other
modules to refer to it. A file declares its imports at file scope.
An import can name a module or a public component. Without an alias, the
last segment supplies the local name. `as` supplies a different local name.
A group expands into separate imports with the same prefix.

```rust
use server::http::{parse_request, health_status as health};
use server::config as configuration;
```

The compiler rejects duplicate local import names after applying aliases.
It also rejects an import that conflicts with a declaration in the current
module. A path that names both a module and a component is ambiguous.

## Building a package

From the package root, `corboc build` reads `package.toml`, compiles
`src/main.crb` and creates `build/<package-name>`. `build/` is created as needed.
The optional binary section selects a different filename:

```toml
[package]
name = "server"

[bin]
name = "api-server"
```

This produces `build/api-server`. Omitting `[bin]` or its `name` uses
`[package].name`. A binary name is one portable filename component: ASCII
letters, digits, `_`, `-` and `.`, containing at least one letter, digit or `_`.
It cannot be a directory path. Duplicate sections/properties, empty names and
unsupported properties are invalid manifests. Sections may appear in any order.
A dependency's binary setting does not affect the importing package's output.

`corboc build PACKAGE` writes the default output under `PACKAGE/build/`,
independently of the caller's current directory. `corboc build -o OUTPUT` and
`corboc build PACKAGE -o OUTPUT` override the default; a relative `OUTPUT` is
resolved from the caller's directory. As before, an explicit output's parent
directory must exist. Failed compilation preserves the existing executable.

The filename policy appends `.exe` for Windows targets. The native build driver
currently supports macOS ARM64; the other native drivers remain unimplemented.

## Single-package prototype (frozen Rust reference)

From a directory containing `package.toml`:

```sh
corbo-frontend check .
corbo-frontend emit-c . > program.c
```

The compiler resolves imports before invoking the existing verifier and C
backend. The CLI also supports reading a standalone program from standard input.

## External packages and the standard library

```toml
[dependencies]
http_tools = { path = "../http_tools" }
bytes = { git = "https://example.com/bytes.git", rev = "<full commit ID>" }
```

A local path is resolved from the manifest that declares it. Git dependencies
are fetched into temporary checkouts at the exact commit identified by `rev`.
A full commit ID is required. A local Git repository path is also supported.
The dependency key must match the name declared by the dependency. Each
package can access its own package and its direct dependencies. The loader
rejects cycles and two sources for the same package name. Local paths inside
a Git checkout must stay within that checkout.

`std` is a reserved package name. The Rust bootstrap embeds the sources under
`stdlib/src/` when it is built. Every package can import its public components
explicitly, for example `use std::num::min_i64;`. The standard library has no
Corbo package dependencies.

On macOS ARM64, `corboc build PACKAGE -o OUTPUT` also resolves these
dependencies. It uses the installed copy of `std` and invokes `git` from
`PATH` for pinned checkouts. The Corbo manifest reader handles the
`[package]` name, optional `[bin]` name and the inline dependency tables
shown above with bare keys and unescaped single-line strings. Its package graph is bounded to 64 packages
in addition to `std`.

## Target selection

The `#(if: condition) ... #(endif)` annotation selects imports and declarations.
Only the condition is inside the opening annotation. Selected items appear
between `#(if: condition)` and `#(endif)`, outside their parentheses.
The compiler provides the compile-time values `target.os`, `target.family`,
and `target.arch`. They describe the target of the generated binary, including
when cross-compiling.

The compiler evaluates the condition before resolving imports. If it is true,
the items participate in the enclosing scope at the position of the annotation.
The annotations introduce no new scope. If it is false, the items are excluded
from name resolution and collision checks.

```rust
#(if: target.family == "unix")
    use std::sys::unix::FileHandle;
#(endif)

#(if: target.os == "windows")
    use std::sys::win::FileHandle;
#(endif)
```

Each target test compares a property to a string with `==`. Tests can be combined with `&&` and `||`. Conjunction binds more tightly. The `target.pointer_width` property is `"32"` or `"64"` on targets with a known pointer width. The
frontend defaults to the host target. To select a different target, pass
a triple to `check` or `emit-c`, for example:

```sh
corbo-frontend emit-c . --target x86_64-unknown-linux-gnu > program.c
```

This option selects source items. Use a C toolchain for that target to
produce the binary.
