# Compiler repository boundary

The active compiler is maintained in [omework/corboc](https://github.com/omework/corboc).
Its `package.toml` and `src/` are at that repository's root. `compiler/corboc/` has
been removed from the working tree; the earlier din-lang repository retains
its history. This repository begins with a content snapshot.

| Repository | Authoritative contents |
| --- | --- |
| `corbo-lang` (this checkout) | Grammar, normative rules, STD, readable runtime, examples, editor support, historical Python/Rust references and language/STD integration corpus |
| `corboc` | Self-hosted compiler, runtime-resource generator, pinned-source resolver, build/install script, focused compiler regression scripts and fixtures |

No grammar, memory invariant or compiler algorithm changes in this extraction.
The internal source package remains `bootstrap` to preserve its existing imports.
The executable remains `corboc`.

## Pin and build

The compiler's `corbo.lock` pins the shared sources to one exact commit in
`omework/corbo-lang`; consult that file for the current revision.
It names the STD, runtime, grammar, rules and validation-guideline paths within
that commit. The compiler materializes an ignored `.deps/corbo/` checkout.
It rejects the wrong HEAD or locally modified inputs rather than silently
resetting a developer's checkout. Local Git objects can supply that same commit;
uncommitted source changes are not copied into the dependency cache.

From the compiler checkout:

```sh
python3 scripts/corbo_sources.py --from-repo ../corbo-lang
python3 scripts/build.py --seed /absolute/path/to/corboc --verify-self
```

The build installs the pinned STD and `corbo.lock` under `share/corbo/`, the
compiler under `bin/`, and the public C header under `include/`. Installed
`corboc build` retains automatic STD discovery relative to its executable.
A compatible seed is required; the frozen Rust reference does not understand
all current source syntax. No seed binary is added to Git by this extraction.

## Language-repository development tools

Place a compiler checkout beside this checkout as `../corboc`, or set:

```sh
export CORBOC_SOURCE_ROOT=/absolute/path/to/corboc
```

`scripts/compiler_location.py` resolves that source path. Historical compiler
regression commands and `scripts/runtime_sources.py` forward to the compiler
repository. Parser/reference corpus tools use its `src/` and retain stable
`corboc/...` source labels when writing corpus records. STD and Rust-reference
checks stay here. The native registry checks locate moved fixture sources through
the same resolver.

When changing runtime/STD code, commit the desired shared-source revision,
update `corbo.lock` deliberately, prepare that revision, regenerate runtime
resources and validate the compiler. The generator does not silently consume
an arbitrary neighboring working tree. Historical cycle reports keep the paths
and commands used for their original executions.

[Extraction evidence](cycles/COMPILER_REPOSITORY_SPLIT.md).
