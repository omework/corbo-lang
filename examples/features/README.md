# Complete feature examples

Each directory is a self-contained package with `package.toml` and `src/main.crb`.
The root README includes the same source verbatim. `manifest.json` records the
expected outputs; its order is the README's learning sequence.

```sh
mkdir -p build
corboc build examples/features/pools -o build/example
./build/example
python3 validation/check_documentation.py --corboc ../corboc/build/install/bin/corboc
```

The checker passes this checkout's STD explicitly, compiles at O1 with fatal
UBSan and executes the result in its own retained directory. The `file` and
`buffered` examples create/delete `demo.bin` there. `network` uses a local
loopback UDP socket and an OS-assigned port. No external network peer is needed.

These are focused examples, not a language-safety proof or a platform-wide
validation campaign. See [the cycle report](../../docs/cycles/DOCUMENTATION_CYCLE.md).

- [An explicit growth budget in Corbo](budget/src/main.crb)
- [A synchronous entry point](hello/src/main.crb)
- [Primitives and checked operators](numbers/src/main.crb)
- [Expressions and control flow](control/src/main.crb)
- [Functions, tuples and destructuring](tuples/src/main.crb)
- [Structs, constants and receiver modes](methods/src/main.crb)
- [Enums and pattern matching](enums/src/main.crb)
- [Result, Option and early propagation](errors/src/main.crb)
- [Moves and explicit copies](moves/src/main.crb)
- [Shared borrows and mutable reborrows](borrows/src/main.crb)
- [Fixed arrays, structural repetition and slices](arrays/src/main.crb)
- [Fixed-capacity pools and allocation handles](pools/src/main.crb)
- [Receivers and placement across scopes](placement/src/main.crb)
- [Destruction before storage release](destruction/src/main.crb)
- [Datastack budgets, local regions and page reclamation](regions/src/main.crb)
- [Vectors and extraction](vector/src/main.crb)
- [HashMap lookup, replacement and removal](map/src/main.crb)
- [UTF-8 text and caller-owned bytes](text/src/main.crb)
- [Closures and explicit callable passing](closures/src/main.crb)
- [STD iterator pipelines](iter/src/main.crb)
- [Contracts on generic structs](generic/src/main.crb)
- [Static structural type contracts](contracts/src/main.crb)
- [Packages, modules, visibility and aliases](modules/src/main.crb)
- [Conditional compilation](target/src/main.crb)
- [Futures, suspension and execution branches](async/src/main.crb)
- [Native threads and captured loans](threads/src/main.crb)
- [Blocking work from an async context](blocking/src/main.crb)
- [Files, errors and caller-provided buffers](file/src/main.crb)
- [Buffered I/O through structural contracts](buffered/src/main.crb)
- [Typed network endpoints and datagrams](network/src/main.crb)
- [Hashes and encodings with bounded output](encoding/src/main.crb)
- [Compression with an explicit workspace](compression/src/main.crb)
- [Unchecked C, typed operands and native assembly](foreign/src/main.crb)
