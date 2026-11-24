# Corbo for Vim and Neovim

Install from the Corbo repository root. Copy the package for your editor.

**Vim on macOS or Linux**

```sh
dest="$HOME/.vim/pack/corbo/start/corbo"
mkdir -p "$dest"
cp -R ide/vim/ftdetect ide/vim/ftplugin ide/vim/syntax "$dest/"
```

**Neovim on macOS or Linux**

```sh
dest="${XDG_DATA_HOME:-$HOME/.local/share}/nvim/site/pack/corbo/start/corbo"
mkdir -p "$dest"
cp -R ide/vim/ftdetect ide/vim/ftplugin ide/vim/syntax "$dest/"
```

**Vim on Windows (PowerShell)**

```powershell
$dest = Join-Path $HOME 'vimfiles\pack\corbo\start\corbo'
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item -Recurse ide/vim/ftdetect,ide/vim/ftplugin,ide/vim/syntax $dest
```

Enable `filetype plugin on` and `syntax enable` in your Vim configuration if
you have disabled them. Restart the editor and open a `.crb` file.
`:set filetype?` should print `filetype=corbo`. The package also configures
`//` as the line comment. To uninstall, remove the package directory you copied.

## Rust-style colors

Corbo highlight groups link to the corresponding Rust groups, so Rust-specific
colorscheme customizations also apply to Corbo. Declarations, storage modifiers,
conditionals, loops, `async`, `await`, casts and receivers use Rust's categories.
Fallback links supply Vim's normal colors when no Rust buffer has been opened.
The package does not load Rust syntax into Corbo buffers or hardcode colors.

After updating the installed package, restart Vim or Neovim. Inspect the group
under the cursor with `:echo synIDattr(synID(line('.'), col('.'), 1), 'name')`;
inspect its effective highlight group with
`:echo synIDattr(synIDtrans(synID(line('.'), col('.'), 1)), 'name')`.

This aligns Vim syntax colors. Neovim Tree-sitter or semantic highlighting from
other plugins can override syntax groups independently.
