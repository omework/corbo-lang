#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Generate/check STD and runtime references from source documentation."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys
from source_docs import inventory, flatten, documentation, heading, c_inventory, c_documentation

ROOT = Path(__file__).resolve().parents[1]
LICENSES = {'// SPDX-License-Identifier: MIT OR Apache-2.0', '// SPDX-License-Identifier: (MIT OR Apache-2.0) AND BSD-3-Clause'}


def collect(path):
    """Require module/declaration/member comments and retain source-linked metadata."""
    source = path.read_text(encoding='utf-8')
    lines = source.splitlines()
    if not lines or lines[0] not in LICENSES:
        raise ValueError(f'{path.relative_to(ROOT)}: missing SPDX header')
    summary = []
    for line in lines[1:]:
        if not line.startswith('//!'): break
        summary.append(line[3:].strip())
    if not any(summary): raise ValueError(f'{path.relative_to(ROOT)}: missing module documentation')
    entries, annotations = inventory(source)
    for entry in flatten(entries):
        if not documentation(source, entry, annotations):
            line = source.count('\n',0,entry.start)+1
            raise ValueError(f'{path.relative_to(ROOT)}:{line}: missing documentation for {entry.owner or ""}::{entry.name}')
    return source, summary, entries, annotations


def render(runtime=False):
    """Render public STD symbols or every internal Corbo runtime entry point."""
    source_root = ROOT / ('runtime/corbo' if runtime else 'stdlib/src')
    files = sorted(source_root.rglob('*.crb'))
    modules = defaultdict(list); count = 0
    for path in files:
        source, summary, entries, annotations = collect(path)
        count += len(list(flatten(entries)))
        if not runtime and path.relative_to(source_root).parts[0] == 'sys': continue
        module = ('runtime::'+path.stem if runtime else '::'.join(('std',*path.relative_to(source_root).parts[:-1])))
        if not runtime and path.relative_to(source_root).parts[0] == 'runtime':
            module = '::'.join(path.relative_to(source_root).parts[:-1])
        modules[module].append((path,source,summary,entries,annotations))
    title = 'Corbo runtime source reference' if runtime else 'Corbo standard library reference'
    output = ['# '+title, '', 'Generated from source documentation. Do not edit this reference by hand.', '']
    if runtime:
        output += ['These are internal runtime entry points, not ordinary public Corbo APIs.',
                   'Raw addresses require live, aligned storage and the documented synchronization.',
                   'The [runtime guide](../runtime/corbo/README.md) explains the checked/unchecked boundary.',
                   'The [C ABI](../runtime/corbo_runtime.h) and [C reference](../runtime/README.md) retain their source comments.', '']
    else:
        output += ['Public declarations and their target conditions are listed below.',
                   'Implementation fields are shown for context; listing them does not grant public field access.',
                   'Internal and platform helpers are documented in the linked source files.',
                   'Compiler-backed collection methods are described in the [collection API guide](COLLECTIONS_API.md).', '']
    flag = ' --runtime' if runtime else ''
    name = 'RUNTIME.md' if runtime else 'STDLIB.md'
    output += [f'Regenerate with `python3 scripts/stdlib_docs.py{flag} > docs/{name}`.', '', '## Modules', '']
    selected={}
    for module, sources in sorted(modules.items()):
        public_types = {e.name for _,_,_,es,_ in sources for e in es if e.public and e.kind in ('struct','enum','type')}
        rows=[]
        for path,source,summary,entries,annotations in sources:
            visible=[e for e in entries if runtime or ((e.owner in public_types) if e.owner else e.public) and not e.name.startswith('__din_')]
            if visible: rows.append((path,source,summary,visible,annotations))
        if rows:
            selected[module]=rows
            output.append(f'- [`{module}`](#{module.replace("::", "")})')
    for module, sources in selected.items():
        output.extend(('',f'## `{module}`'))
        for path,source,summary,entries,annotations in sources:
            link='../'+path.relative_to(ROOT).as_posix()
            output.extend(('',*summary,''))
            previous=None
            for entry in entries:
                if entry.conditions != previous:
                    if entry.conditions: output.extend(('Available when '+ ' and '.join(f'`{c}`' for c in entry.conditions)+'.',''))
                    previous=entry.conditions
                name=(entry.owner+'::' if entry.owner else '')+entry.name
                line=source.count('\n',0,entry.start)+1
                output.extend((f'### `{name}`','',f'[{path.name}:{line}]({link}#L{line})','', '```rust',heading(source,entry),'```','',documentation(source,entry,annotations),''))
                if entry.children:
                    output += ['Members:', '']
                    for member in flatten(entry.children):
                        line=source.count('\n',0,member.start)+1
                        doc=documentation(source,member,annotations).replace('\n',' ')
                        label='variant' if member.kind=='variant' else 'implementation field'
                        symbol=(member.owner.split('::',1)[1]+'.' if '::' in (member.owner or '') else '')+member.name
                        output.append(f'- [`{symbol}`]({link}#L{line}) ({label}): {doc}')
                    output.append('')
    if runtime:
        import ast
        for helper in (ROOT/'runtime/corbo').glob('*.py'):
            files.append(helper)
            tree=ast.parse(helper.read_text())
            if not ast.get_docstring(tree): raise ValueError(str(helper)+': missing module docstring')
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and not ast.get_docstring(node): raise ValueError(str(helper)+': missing docstring for '+node.name)
        output += ['', '## C ABI and comparison sources', '',
                   'These declarations describe the C boundary/reference, not new checked-language APIs.', '']
        for path in sorted((ROOT/'runtime').rglob('*')):
            if not path.is_file() or path.suffix not in ('.h','.c','.inc'): continue
            source=path.read_text(); entries=c_inventory(source)
            if '/** @file' not in source: raise ValueError(str(path)+': missing C module documentation')
            files.append(path)
            if not entries: continue
            output += ['### `'+path.relative_to(ROOT).as_posix()+'`', '']
            for entry in flatten(entries):
                doc=c_documentation(source,entry)
                if not doc: raise ValueError(str(path)+': missing C documentation for '+entry.name)
                count+=1
                line=source.count('\n',0,entry.start)+1
                link='../'+path.relative_to(ROOT).as_posix()
                output += [f'- [`{entry.name}`]({link}#L{line}): '+doc, '']
    return '\n'.join(output).rstrip()+'\n',len(files),count


def main():
    """Write one reference, or check both coverage and generated-file freshness."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',action='store_true',help='emit the internal runtime reference')
    parser.add_argument('--check',action='store_true',help='check both source inventories and references')
    args=parser.parse_args()
    try:
        if args.check:
            for runtime,name in [(False,'STDLIB.md'),(True,'RUNTIME.md')]:
                reference,files,count=render(runtime)
                if (ROOT/'docs'/name).read_text()!=reference: raise ValueError(f'docs/{name} is stale; regenerate it with scripts/stdlib_docs.py'+(' --runtime' if runtime else ''))
                print(f'Checked {files} files and {count} documented declarations/members ({name}).')
        else: sys.stdout.write(render(args.runtime)[0])
    except (OSError,ValueError) as error: parser.exit(1,str(error)+'\n')


if __name__=='__main__': main()
