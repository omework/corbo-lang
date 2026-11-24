#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Source-position inventory for documentation; this is not a language parser."""
from dataclasses import dataclass, field
import re

TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|->|::|[^\s]')

@dataclass
class Entry:
    """One documented declaration/member and its original source position."""
    kind: str
    name: str
    start: int
    head_end: int
    public: bool = False
    owner: str | None = None
    conditions: tuple = ()
    children: list = field(default_factory=list)


def tokens(source):
    """Ignore comments while retaining byte/character offsets for ASCII syntax."""
    return [(m[0], m.start(), m.end()) for m in TOKEN.finditer(source)
            if not m[0].startswith(('//', '/*'))]


def end_group(ts, at):
    """Find the token after a balanced bracketed source group."""
    pairs = {'(': ')', '[': ']', '{': '}'}
    if ts[at][0] == '<': pairs['<'] = '>'
    stack = [pairs[ts[at][0]]]
    at += 1
    while stack and at < len(ts):
        word = ts[at][0]
        if word in pairs: stack.append(pairs[word])
        elif word == stack[-1]: stack.pop()
        at += 1
    if stack: raise ValueError('Unclosed source group')
    return at


def split_members(ts, low, high):
    """Split fields/variants on commas outside their nested type/payload groups."""
    start = low
    while low < high:
        word = ts[low][0]
        if word in ('(', '[', '{', '<'): low = end_group(ts, low); continue
        if word in (',', ';'):
            if start < low: yield start, low
            start = low + 1
        low += 1
    if start < high: yield start, high


def inventory(source):
    """Read Corbo declaration heads, owners and member positions, skipping native code."""
    ts = tokens(source); entries = []; annotation_ends = {}; conditions = []
    def scan(low, high, owner=None, parent_entry=None):
        at = low
        while at < high:
            word = ts[at][0]
            if word == '#' and at + 1 < high and ts[at + 1][0] == '(':
                stop = end_group(ts, at + 1)
                annotation_ends[ts[stop - 1][2]] = ts[at][1]
                head = source[ts[at][1]:ts[stop-1][2]]
                if head.startswith('#(if:'): conditions.append(head[6:-1].strip())
                elif head.startswith('#(endif') and conditions: conditions.pop()
                at = stop; continue
            if word == '@' and at + 1 < high and ts[at + 1][0] in ('c', 'asm'):
                at += 2
                if ts[at][0] == '(': at = end_group(ts, at)
                at = end_group(ts, at); continue
            if parent_entry is not None and re.fullmatch(r'[A-Za-z_]\w*', word) and word not in ('pub', 'fn', 'async', 'const', 'struct', 'enum', 'type'):
                data_kind = parent_entry.kind
                field = data_kind == 'struct' and at + 1 < high and ts[at + 1][0] == ':'
                variant = data_kind == 'enum'
                if field or variant:
                    stop = at + 1
                    while stop < high and ts[stop][0] not in (';', ','):
                        if ts[stop][0] in ('(', '[', '{', '<'): stop = end_group(ts, stop)
                        else: stop += 1
                    child = Entry('field' if field else 'variant', word, ts[at][1], ts[stop-1][2], parent_entry.public, owner, tuple(conditions))
                    if variant and at + 1 < stop and ts[at+1][0] == '{':
                        for first,last in split_members(ts,at+2,stop-1):
                            child.children.append(Entry('field',ts[first][0],ts[first][1],ts[last-1][2],parent_entry.public,owner+'::'+word,tuple(conditions)))
                    parent_entry.children.append(child)
                    at = stop + (stop < high)
                    continue
            if word in ('fn', 'struct', 'enum', 'impl', 'const', 'type') and at + 1 < high and re.fullmatch(r'\w+', ts[at+1][0]):
                kind = word; name = ts[at+1][0]; begin = at
                while begin > low and ts[begin-1][0] in ('pub', 'async', 'extern'): begin -= 1
                public = any(t[0]=='pub' for t in ts[begin:at])
                cursor = at + 2
                while cursor < high and ts[cursor][0] not in ('{', ';'):
                    if ts[cursor][0] in ('(', '[', '<'): cursor = end_group(ts,cursor)
                    else: cursor += 1
                if cursor >= high: raise ValueError('Unterminated declaration '+name)
                entry = Entry(kind,name,ts[begin][1],ts[cursor][1],public,owner,tuple(conditions))
                if kind != 'impl': entries.append(entry)
                if ts[cursor][0] == '{':
                    stop=end_group(ts,cursor)
                    if kind=='impl': scan(cursor+1,stop-1,name)
                    elif kind in ('struct','enum'):
                        scan(cursor+1, stop-1, name, entry)
                    at=stop
                else: at=cursor+1
                continue
            at+=1
    scan(0,len(ts))
    return entries, annotation_ends


def documentation(source, entry, annotations):
    """Read /// documentation across intervening annotations, without guessing prose."""
    at=entry.start; pieces=[]
    while True:
        at=len(source[:at].rstrip())
        if at in annotations:
            at=annotations[at];continue
        start=source.rfind('\n',0,at)+1
        line=source[start:at].strip()
        if line.startswith('///'):
            pieces.append(line[3:].strip());at=start;continue
        break
    return '\n'.join(reversed(pieces))


def flatten(entries):
    """Yield declarations followed by their fields/variants in source order."""
    for entry in entries:
        yield entry
        yield from flatten(entry.children)


def heading(source, entry):
    """Render a compact signature without implementation text or comments."""
    return ' '.join(re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',source[entry.start:entry.head_end]).split())


def c_inventory(source):
    """Locate top-level C functions and named/typedef ABI types, never body calls."""
    ts=tokens(source); entries=[]; at=0; start=0
    while at<len(ts):
        word=ts[at][0]
        # Preprocessor text is outside this declaration inventory.
        if word=='#':
            line=source.find('\n',ts[at][1]);line=len(source) if line<0 else line
            while at<len(ts) and ts[at][1]<line:at+=1
            start=at;continue
        if word in ('struct','union'):
            cursor=at+1
            named=cursor<len(ts) and re.fullmatch(r'\w+',ts[cursor][0])
            name=ts[cursor][0] if named else None
            if named:cursor+=1
            if cursor<len(ts) and ts[cursor][0]=='{':
                stop=end_group(ts,cursor)
                if name is None and stop<len(ts):name=ts[stop][0]
                begin=ts[start][1] if start<len(ts) else ts[at][1]
                entry=Entry('c_type',name or 'anonymous',begin,ts[cursor][1])
                field_start=cursor+1; pos=field_start
                while pos<stop-1:
                    if ts[pos][0] in ('(', '[', '{'):
                        pos=end_group(ts,pos);continue
                    if ts[pos][0]==';':
                        if field_start<pos:
                            declaration=source[ts[field_start][1]:ts[pos][1]]
                            callback=re.search(r'\(\s*\*\s*(\w+)\s*\)',declaration)
                            if callback:member=callback[1]
                            else:
                                # Field groups can share one C type (size_t x,y).
                                parts=re.split(',',declaration)
                                names=[]
                                for part in parts:
                                    words=re.findall(r'[A-Za-z_]\w*',part.split('[')[0])
                                    if words:names.append(words[-1])
                                member=','.join(names)
                            entry.children.append(Entry('c_field',member,ts[field_start][1],ts[pos][1],owner=name))
                        field_start=pos+1
                    pos+=1
                entries.append(entry)
                at=stop
                while at<len(ts) and ts[at][0]!=';':at+=1
                at+=1;start=at;continue
        if re.fullmatch(r'[A-Za-z_]\w*',word) and at+1<len(ts) and ts[at+1][0]=='(':
            stop=end_group(ts,at+1)
            if stop<len(ts) and ts[stop][0]=='{':
                entries.append(Entry('c_fn',word,ts[start][1],ts[stop][1]))
                at=end_group(ts,stop);start=at;continue
            if stop<len(ts) and ts[stop][0]==';' and at>start and ts[start][0]!='_Static_assert':
                entries.append(Entry('c_fn',word,ts[start][1],ts[stop][1]))
                at=stop+1;start=at;continue
        if word==';':
            if start<at and ts[start][0]=='typedef':
                entries.append(Entry('c_type',ts[at-1][0],ts[start][1],ts[at][1]))
            at+=1;start=at;continue
        at+=1
    return entries


def c_documentation(source, entry):
    """Read the Doxygen block immediately preceding a C declaration."""
    prefix=source[:entry.start].rstrip()
    if not prefix.endswith('*/'):return ''
    start=prefix.rfind('/**')
    if start<0 or '*/' in prefix[start:-2]:return ''
    return '\n'.join(re.sub(r'^\s*\* ?', '', line).strip() for line in prefix[start+3:-2].splitlines()).strip()
