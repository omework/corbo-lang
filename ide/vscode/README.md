# Corbo for Visual Studio Code

The extension registers `.crb` as Corbo and provides syntax highlighting,
line comments, bracket matching, and automatic closing of brackets and quotes.
It highlights `@c` blocks with VS Code's built-in C grammar and recognizes
ARM64 and x86-64 instructions, registers, labels, and Corbo operands in
`@asm` blocks. This is editor support. The current compiler only accepts the
inline assembly form.

## Rust-style keyword colors

Corbo keywords expose the same TextMate categories as VS Code's bundled Rust
syntax, alongside Corbo-specific scopes. Your current theme chooses the colors:
`fn`, `let`, `pub`, `mut`, `async`, `use`, declarations and control flow therefore
use their corresponding Rust categories. The extension does not change your theme
or add global color overrides. Embedded C and assembly keep their own highlighting.

This aligns syntax colors, not Rust Analyzer's semantic highlighting. Exact colors
can still differ in themes with rules restricted to an entire `source.rust` context
or when Rust semantic tokens override syntax colors.

After updating the extension, run **Developer: Reload Window**. To inspect a token,
use **Developer: Inspect Editor Tokens and Scopes**; keywords should include a
Rust-compatible scope such as `keyword.other.fn.rust`.

## Install locally

From the repository root, launch a window with the extension loaded for
development.

```sh
code --extensionDevelopmentPath="$PWD/ide/vscode" examples
```

For a persistent installation, package the extension as a VSIX. Run these
commands from the repository root with Node.js and the `code` CLI available.

```sh
mkdir -p build
cd ide/vscode
npx --yes --package @vscode/vsce vsce package --out ../../build/corbo.vsix
code --install-extension ../../build/corbo.vsix
```

You can also install the VSIX through **Extensions → … → Install from VSIX…**.
Open a `.crb` file and check for **Corbo** in the language indicator. Use
**Developer: Inspect Editor Tokens and Scopes** to inspect a highlighted token.
Remove the extension from the Extensions panel to uninstall it.

See the [VS Code syntax highlighting guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
for more on TextMate scopes and themes.

The extension is available under [MIT](LICENSE) or [Apache 2.0](LICENSE-APACHE).
