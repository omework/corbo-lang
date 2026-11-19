# Package-root build defaults

This build/CLI change adds `corboc build` from a package root. Its default
output is `build/<package-name>`; optional `[bin].name` selects a different
filename. `corboc build PACKAGE` keeps its default output under that package.
`-o OUTPUT` overrides the configured name and remains relative to the caller's
working directory. The default directory is created automatically.

The README now demonstrates the package-root command, optional binary settings
and both explicit-output forms. [Module documentation](../MODULES.md) records
the accepted manifest syntax and filename constraints. No source-language grammar
or memory rule changed, and the Rust reference remains frozen.

The companion compiler's `validation/check_package_build.py` completed 18
focused checks on macOS ARM64: nine successful build-and-run commands, eight
expected failures, and a separate check that failed compilation preserves the
previous executable and cleans its workspace. Module/path/STD dependencies,
section order, directory reuse and paths containing spaces are included.
The language README example/source synchronization and generated API-reference
freshness checks pass.

The native build driver currently supports macOS ARM64 only. The Windows
filename policy adds `.exe`, but no Windows native build execution is claimed.
Other native drivers remain unimplemented; Windows ARM64 execution is deferred.
These functional checks do not constitute an independent safety audit.

See `docs/PACKAGE_BUILD_DEFAULTS_CYCLE.md` in the companion corboc repository
for implementation details, commands and retained-artifact locations.
