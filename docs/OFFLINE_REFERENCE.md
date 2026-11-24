[Français](OFFLINE_REFERENCE-fr.md)

# Offline HTML reference

Run `corboc doc` after installing the compiler. It opens the installed reference
in your browser and serves it on IPv4 loopback. The operating system chooses an
available port unless `--port PORT` is supplied; `--port 0` is also automatic.
`--no-open` is useful over SSH or when opening the URL manually. Stop with Ctrl+C.
No command-line manual is installed.

The reference includes every documented STD declaration and member, including
target-specific and internal sources. Compiler-owned types and APIs are supplied
by a separate checked-in catalog: primitives, references, arrays, slices, tuples,
callables, allocation descriptors, native collections, Result/Option, task handles,
intrinsics and annotations. Compiler/runtime contracts are labeled separately
from ordinary source declarations. The public C runtime ABI is included too.

A type has its own page with signatures, method anchors, target conditions and
source links. Internal sources are marked; listing a private field does not grant
access. The language tour contains complete feature examples. Design guides are
bundled with historical material clearly distinguished from current API entries.

## Search and navigation

- Press `/` or Ctrl/Cmd+K to focus search.
- Search by short or qualified name, signature, or description; multiple words narrow results.
- Use up/down and Enter to open a result; Escape clears search.
- Browse packages in the sidebar and follow type names in signatures.
- Follow source links to the exact bundled declaration line.

All assets and the search index are local, with no external fonts or dependencies.
The generated `index.html` also works directly with file:// when a browser allows
local scripts. The loopback server avoids browser file-origin restrictions.

## Generation and installation

The compiler repository owns the HTML generator and the compiler API catalog:

```sh
python3 ../corboc/scripts/stdlib_html.py \
  --corbo-root . --out build/std-reference
```

`corboc` installation builds the same reference automatically under
`PREFIX/share/corbo/docs/`, beside the pinned STD. Metadata records the Corbo
revision and compiler-catalog digest. The executable does not require Python to
serve the resulting files. Rebuild the installation to refresh the snapshot.
The server is implemented in Corbo using the existing synchronous File/TCP APIs;
native code is limited to opening the desktop browser.

The source-comment inventory remains authoritative for source-defined APIs.
Maintain `corboc/docs/BUILTIN_REFERENCE.json` when a compiler-provided interface
changes. Do not invent empty STD method bodies just to make them appear in docs.
