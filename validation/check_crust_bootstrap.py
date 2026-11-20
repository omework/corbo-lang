"""Compare the Crust bootstrap AST and static tree with the Rust frontend."""
from pathlib import Path
from check_rust_destructors import ASYNC as RUST_DROP_ASYNC, INLINE as RUST_DROP_INLINE, POOLED as RUST_DROP_POOLED
from check_rust_regions import ACCEPTED as RUST_REGION_ACCEPTED, EXHAUSTED as RUST_REGION_EXHAUSTED
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "build/rust_frontend/debug/corbo-frontend"
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from compiler_location import compiler_root
PACKAGE = compiler_root()
KINDS = (
    "programme", "fn", "scope", "paramètre", "type", "liaison", "return",
    "nom", "instruction", "littéral", "résultat", "binaire", "unaire",
    "emprunt", "indirection", "appel", "appel méthode", "projection", "indice",
    "groupe", "tuple", "affectation", "while", "break", "continue", "yield",
    "if", "loop", "struct", "enum", "variante", "champ", "use", "import member",
    "import alias", "async fn", "nom qualifié", "construction", "await",
    "match", "bras", "motif nom", "motif appel", "motif unité", "tableau",
    "tableau répété", "plage", "tuple let", "tuple binding", "impl", "unchecked", "asm", "opérande asm", "motif variante", "motif champ", "closure", "move bloc", "move nommé", "annotation", "verrou", "verrou lié au résultat",
    "fin de branche", "taille de datastack", "nombre de régions", "extern", "unsafe", "pool", "type libre", "paramètre de type", "type avec",
    "type exact", "unused", "capacité", "capacités", "initialiseur pool", "région", "const",
)
FACTS = (
    "Syntax", "Use", "NamedMove", "Borrow", "Pool", "AddressCandidate",
    "Collection", "Capture", "Exit", "Await", "Projection", "Call", "Write",
    "Branch", "Suspend",
)
VALID = (
    "",
    "const LIMIT: u8 = 2; struct Mode {} impl Mode { const FLOOR: i64 = -1; } fn main() { print(Mode::FLOOR); }",
    "fn main() {{}}\n",
    "fn f(x: i64, mut y: u8,) -> i64 { let mut a: i64 = x; let b = 1; return a; }",
    'fn f(x: bool) -> bool { let y = "é"; true }',
    "fn main() { return; }",
    "fn f() { a+b*c-d; f((a+b), x.foo(2), (4,5),); a[2].field; }",
    "fn f() { let x = !true || -a >= b >> 2; let y = &mut a[0]; *x as u64 }",
    "fn f(x: &mut [i64; 4], f: fn(i64) -> (i64, i64)) -> Map<Key, Vec<i64>> {}",
    "fn f(){ while x > 1 { x -= 1; if x == 2 { continue; } } "
    "let y = loop { break 2; }; if y { 1 } else if z { 2 } else { 3 } }",
    "use std::io::sync::{File as Input, FileError}; pub struct S { n: i64 } "
    "impl S { fn get(&self) -> i64 { (*self).n } } "
    "enum E { Empty, Full { n: i64 }, } async fn run() { f().await; }",
    "fn f(){ let a = [1 + 2; 4]; let b = &a[1..3]; let (x, y) = (.5, 0xFF); "
    "match data { Ok(v) => { v }, Err(e) => { e }, } }",
    "fn f(){ let c = move |x: i64| -> i64 { x }; let d = || { 1 }; move { move c; c() } }",
    '#(datastack: size=4G, region_size=100M) #(branch: join=result.join()) '
    'fn f() #(stack_region: max_size=4M, count=8) #(free_pages) {}',
    '#(lock: on=self, through_result=true) fn f() {} #(branch) fn g() {}',
    'extern "C" fn get() -> i64; fn main() { unsafe { get(); } }',
    'fn f() { let p = pool<i64>(2); HashMap<i64, Point>::new(); }',
    '#(type: R *) #(type: T<R> with { fn id(&self) -> i64; }) fn f(t: T) -> R {}',
    '#(directive: async_pool_sizes={example::work: 2, other: 4}) fn f() {}',
    'fn f(){ p.new({n: 2}); p.new({}); p.new(n: 2); bytes.try_slice(1..3); bytes.try_slice(); }',
    "struct point {} fn f(){ point {} }",
    "fn f(mut x: i64) { let a = move || { let b = || { x; x; }; return x; }; "
    "while x > 0 { loop { if x > 1 { break; } continue; } break; } return; }",
    "fn f(x: i64) { let y = x; { let x = y; x; } y; }",
    "fn f(x: i64) { { move x; x; } x; }",
    "fn f(v: i64) { let a = || { v }; match v { Some(x) => { x }, _ => { v } } }",
    "fn f() { let (a,b) = (1,2); while a < b { let a = b; a; } }",
    (ROOT / "stdlib/src/env/args.crb").read_text(),
    'fn f() { @unchecked { @asm { mov ${value}, 1 // } ${comment}\n } } }',
    '#(if: target.family == "unix" { use std::io::sync::File; })'
    '#(if: target.os == "not-a-target" { fn syntax_is_excluded( }) fn main() {}',

    *(path.read_text() for path in sorted((PACKAGE / "src").rglob("*.crb"))),
    *(path.read_text() for path in sorted((ROOT / "stdlib/src").rglob("*.crb"))),
)
INVALID = (
    "fn f(x:) {}", "fn f(x:i64 y:i64) {}", "fn f() -> {}",
    "fn f(){ let a = ; }", "fn f(){ return 1 }", "fn f(){ let mut",
    "#(datastack: size=0M) fn f() {}", "#(datastack: size=0x4M) fn f() {}",
    "fn f() { @asm { nop } }", "use a::{};", "enum E {}", "fn f(){ a < b < c; }",
)


def rust_ast(source):
    dump = subprocess.check_output([FRONTEND, "program"], input=source, text=True)
    tokens, syntax = dump.split("syntax: Syntax", 1)
    spans = [
        tuple(map(int, match))
        for match in re.findall(r"span: Span \{\s+start: (\d+),\s+end: (\d+),", tokens)
    ]
    nodes = []
    for node in syntax.split("scopes:", 1)[0].split("Node {")[1:]:
        name = re.search(r"name: Some\(\s*(\d+)", node)
        kind, start, end = re.search(
            r'kind: "(.*?)",\s+start: (\d+),\s+end: (\d+)', node
        ).groups()
        children = node.split("children: [", 1)[1].split("],", 1)[0]
        children = [int(i) for i in re.findall(r"NodeId\(\s*(\d+),\s*\)", children)]
        bounds = spans[int(start)][0], spans[int(end) - 1][1]
        operand = re.search(r"asm_operand: Some\(\s*Span \{\s+start: (\d+),\s+end: (\d+),", node)
        if operand:
            bounds = tuple(map(int, operand.groups()))
        public = int("public: true" in node)
        nodes.append((KINDS.index(kind), *bounds, *(spans[int(name[1])] if name else (0, 0)),
                      public, children))
    nodes[-1] = (0, 0, len(source.encode()), 0, 0, 0, nodes[-1][-1])
    root = len(nodes) - 1
    ast, order = project(nodes, root)
    scopes_section, rest = syntax.split("scopes:", 1)[1].split("\n    bindings:", 1)
    binding_section, points_section = rest.split("\n    points:", 1)
    scopes = scopes_section.split("Scope {")[1:]
    scope_nodes = [int(re.search(r"syntax: NodeId\(\s*(\d+)", scope)[1]) for scope in scopes]
    entrants = {}
    for scope in scopes:
        entry = re.search(r"entry: Some\(\s*PointId\(\s*(\d+)", scope)
        parent = re.search(r"parent: Some\(\s*ScopeId\(\s*(\d+)", scope)
        if entry and parent:
            entrants[int(entry[1])] = int(parent[1])
    def binding_details(binding):
        node = int(re.search(r"syntax: NodeId\(\s*(\d+)", binding)[1])
        ty = re.search(r"ty: Some\(\s*NodeId\(\s*(\d+)", binding)
        initializer = re.search(r"initializer: Some\(\s*NodeId\(\s*(\d+)", binding)
        return node, ("mutable: true" in binding, int(ty[1]) if ty else None,
                      int(initializer[1]) if initializer else None)

    bindings = dict(map(binding_details, binding_section.split("Binding {")[1:]))
    binding_nodes = list(bindings)
    positions = {node: i for i, node in enumerate(order)}
    static = {}
    point_text, captures_text = points_section.split("\n    captures:", 1)
    points = point_text.split("Point {")[1:]
    point_nodes = [positions[int(re.search(r"syntax: NodeId\(\s*(\d+)", point)[1])]
                   for point in points]
    operands = {}
    ends = []
    for point_id, point in enumerate(points):
        if "fact: EndOfScope" in point:
            ends.append(point_nodes[point_id])
            continue
        operand_text = point.split("operands: [", 1)[1].split("],", 1)[0]
        operands[point_nodes[point_id]] = [
            point_nodes[int(i)] for i in re.findall(r"PointId\(\s*(\d+)", operand_text)
        ]
        node = int(re.search(r"syntax: NodeId\(\s*(\d+)", point)[1])
        scope = int(re.search(r"scope: ScopeId\(\s*(\d+)", point)[1])
        use = re.search(r"(?:binding|source): Some\(\s*BindingId\(\s*(\d+)", point)
        fact = FACTS.index(re.search(r"fact: (\w+)", point)[1])
        destination = re.search(r"destination: Some\(\s*NodeId\(\s*(\d+)", point)
        binding_mutable, ty, initializer = bindings.get(node, (False, None, None))
        mutable = "mutable: true" in point or binding_mutable
        static[positions[node]] = (
            positions[scope_nodes[scope]],
            positions[binding_nodes[int(use[1])]] if use else 0,
            positions[scope_nodes[entrants[point_id]]] if point_id in entrants else 0,
            int(node in binding_nodes), fact, int(mutable),
            positions[int(destination[1])] if destination else 0, int("moving: true" in point),
            positions[ty] if ty is not None else 0, positions[initializer] if initializer is not None else 0,
        )
    captures = set()
    for capture in captures_text.split("Capture {")[1:]:
        binding = int(re.search(r"source: BindingId\(\s*(\d+)", capture)[1])
        closure = int(re.search(r"closure: NodeId\(\s*(\d+)", capture)[1])
        captures.add((positions[closure], positions[binding_nodes[binding]]))
    return ast, [static[i] for i in range(len(ast))], captures, operands, sorted(ends)


def project(nodes, root):
    rows = []
    order = []

    def visit(index, parent):
        kind, start, end, name_start, name_end, public, children = nodes[index]
        position = len(rows)
        order.append(index)
        rows.append((kind, parent, start, end, name_start, name_end, public))
        for child in children:
            visit(child, position)

    visit(root, 0)
    return rows, order


def syntax_rows(raw):
    assert len(raw) % 7 == 0
    rows = list(zip(*[iter(raw)] * 7, strict=True))
    assert rows and rows[0][:2] == (0, 0)
    children = [[] for _ in rows]
    for index, row in enumerate(rows[1:], 1):
        children[row[1]].append(index)
    # Tuple bindings follow their initializer in the Rust parser's child order.
    for siblings in children:
        siblings.sort(key=lambda i: (
            rows[i][0] in (KINDS.index("tuple binding"), KINDS.index("type avec"), KINDS.index("type exact")),
            rows[i][2],
        ))
    nodes = [(kind, *spans, children[i]) for i, (kind, _, *spans) in enumerate(rows)]
    ordered, order = project(nodes, 0)
    assert len(ordered) == len(rows)
    return ordered, order


def crust_ast(output):
    raw = list(map(int, output.split()))
    split = raw.index(-1)
    section_end = raw.index(-2, split + 1)
    operand_start = raw.index(-3, split + 1)
    ends_start = raw.index(-4, operand_start + 1)
    graph = list(zip(*[iter(raw[split + 1:operand_start])] * 10, strict=True))
    operand_pairs = list(zip(*[iter(raw[operand_start + 1:ends_start])] * 2, strict=True))
    captures = list(zip(*[iter(raw[section_end + 1:])] * 2, strict=True))
    end_nodes = raw[ends_start + 1:section_end]
    raw = raw[:split]
    ordered, order = syntax_rows(raw)
    assert len(graph) == len(ordered)
    positions = {node: i for i, node in enumerate(order)}
    graph = [
        (*(positions[x] for x in graph[node][:3]), *graph[node][3:6],
         positions[graph[node][6]], graph[node][7], *(positions[x] for x in graph[node][8:]))
        for node in order
    ]
    assert len(captures) == len(set(captures))
    operands = {i: [] for i in range(len(ordered))}
    for point, operand in operand_pairs:
        operands[positions[point]].append(positions[operand])
    ends = sorted(positions[node] for node in end_nodes)
    return (
        ordered, graph, {(positions[closure], positions[source]) for closure, source in captures},
        operands, ends,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path, help="run an existing bootstrap executable")
    options = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        executable = options.bootstrap
        if executable is None:
            executable = work / "bootstrap"
            generated = work / "bootstrap.c"
            with generated.open("w") as out:
                subprocess.run([FRONTEND, "emit-c", PACKAGE], stdout=out, check=True)
            subprocess.run(
                ["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                 "-fno-sanitize-recover=all", generated, "-o", executable], check=True
            )
        else:
            executable = executable.resolve()
        executable_witness = work / "program"
        subprocess.run(
            [FRONTEND, "build", "-o", executable_witness],
            input="fn main(){ let mut p = pool<i64>(2); let a = p.new(3); print(*a); drop(a); }",
            text=True, check=True,
        )
        assert subprocess.check_output([executable_witness], text=True) == "3\n"
        refused = work / "refused"
        result = subprocess.run(
            [FRONTEND, "build", "-o", refused],
            input="fn main(){ let x = 1; drop(x); print(x); }",
            text=True, capture_output=True,
        )
        assert result.returncode != 0 and not refused.exists(), result
        input_path = work / "input.crb"
        corpus = []
        for path in sorted((ROOT / "examples").glob("*.crb")):
            source = path.read_text()
            rust = subprocess.run([FRONTEND, "program"], input=source, capture_output=True, text=True)
            if rust.returncode == 0:
                corpus.append(source)
        for source in (*VALID, *corpus):
            input_path.write_text(source)
            result = subprocess.run([executable, input_path], capture_output=True, text=True)
            assert result.returncode == 0, (source[:100], result.returncode, result.stderr)
            actual, actual_static, actual_captures, actual_operands, actual_ends = crust_ast(result.stdout)
            expected, expected_static, expected_captures, expected_operands, expected_ends = rust_ast(source)
            if actual != expected:
                mismatch = next(((a, e) for a, e in zip(actual, expected) if a != e), None)
                raise AssertionError((source[:80], mismatch, len(actual), len(expected)))
            if actual_static != expected_static:
                mismatch = next(i for i, pair in enumerate(zip(actual_static, expected_static))
                                if pair[0] != pair[1])
                raise AssertionError((source[:80], mismatch, actual[mismatch],
                                      actual_static[mismatch], expected_static[mismatch]))
            assert actual_operands == expected_operands, source[:80]
            assert actual_ends == expected_ends, (source[:80], actual_ends, expected_ends)
            assert actual_captures == expected_captures, (
                source[:80], actual_captures, expected_captures
            )
        for source in INVALID:
            input_path.write_text(source)
            result = subprocess.run([executable, input_path], capture_output=True)
            assert (result.returncode, result.stdout, result.stderr) == (7, b"", b""), source
        checks = (
            ("fn main(){ let x: i32 = 10; print(copy(x)); drop(x); }", 0, None),
            ("fn id(x: i64) -> i64 { x } fn main(){ let x = 3; print(id(x)); }", 0, None),
            ("fn main(){ let mut x = 1; x = copy(x); print(x); }", 0, None),
            ("fn main(){ let x = 1; let y = x; print(x); }", 8, 6),
            ("fn main(){ let x = 1; drop(x); drop(x); }", 8, 7),
            ("fn main(){ let x = 1; { move x; } print(x); }", 8, 6),
            ("fn main(){ let x = 1; x = 2; }", 8, 5),
            ("fn main(){ let x: i32 = -2147483648; let y: u64 = 18446744073709551615; }", 0, None),
            ("fn main(){ let x: u8 = 256; }", 8, 1),
            ("fn main(){ let x: i32 = -2147483649; }", 8, 1),
            ("fn main(){ let x: i32 = 2147483648; }", 8, 1),
            ("fn main(){ copy(); }", 8, 3),
            ("fn id(x: i64) -> i64 { x } fn main(){ id(); }", 8, 8),
            ("fn f(r: &mut i64) -> &mut i64 { &mut *r }", 0, None),
            ("fn f(r: &i64) -> &i64 { &*r }", 0, None),
            ("fn f(r: &i64) -> &mut i64 { &mut *r }", 8, 5),
            ("fn id(r: &i64) -> &i64 { r } "
             "fn f(){ let x = 1; let r = &x; let q: &i64 = id(r); print(*q); }", 0, None),
            ("fn id(r: &i64) -> &i64 { r } "
             "fn f(){ let x = 1; let r = &x; let q: &i32 = id(r); }", 8, 1),
            ("fn hold(a: &i64, n: i64) -> &i64 { a } "
             "fn f(){ let x = 1; let a = &x; let r = hold(a, x); print(*r); }", 8, 5),
            ("fn select(a: &i64, condition: bool, unused: &i64, b: &i64, n: i64) -> &i64 { "
             "if condition { return a; } return b; } "
             "fn f(c: bool){ let x = 1; let mut y = 2; let z = 3; let a = &x; let u = &y; let b = &z; "
             "let r = select(a, c, u, b, 8); y = 4; print(*r); }", 0, None),
            ("fn select(a: &i64, condition: bool, unused: &i64, b: &i64) -> &i64 { "
             "if condition { return a; } return b; } "
             "fn f(c: bool){ let x = 1; let y = 2; let mut z = 3; let a = &x; let u = &y; let b = &z; "
             "let r = select(a, c, u, b); z = 4; print(*r); }", 8, 5),
            ("fn choose(c: bool, a: &i64, b: &i64, d: &i64) -> &i64 { "
             "if c { return a; } else { if c { return b; } else { return d; } } } "
             "fn f(c: bool){ let x = 1; let y = 2; let mut z = 3; let a = &x; let b = &y; let d = &z; "
             "let r = choose(c, a, b, d); z = 4; print(*r); }", 8, 5),
            ("fn choose(c: bool, a: &i64, b: &i64, d: &i64) -> &i64 { "
             "if c { return a; } else { if c { return b; } else { return d; } } } "
             "fn f(c: bool){ let x = 1; let y = 2; let mut z = 3; let a = &x; let b = &y; let d = &z; "
             "let r = choose(c, a, b, d); print(*r); z = 4; }", 0, None),
            ("fn choose(c: bool, a: &i64, b: &i64) -> &i64 { if c { return a; } else { return b; } } "
             "fn f(c: bool){ let x = 1; let y = 2; let a = &x; let b = &y; "
             "let r = choose(c, a, b); print(*r); print(c); }", 8, 6),
            ("fn choose(c: bool, a: &i64, b: &i64) -> &i64 { if c { return a; } else { return b; } } "
             "fn id(r: &i64) -> &i64 { r } "
             "fn f(c: bool){ let x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r = choose(c, a, b); let v = id(r); y = 4; print(*v); }", 8, 5),
            ("fn choose(c: bool, a: &i64, b: &i64) -> &i64 { if c { return a; } else { return b; } } "
             "fn id(r: &i64) -> &i64 { r } "
             "fn f(c: bool){ let mut x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r: &i64 = choose(c, a, b); let v: &i64 = id(r); print(*v); x = 3; y = 4; }", 0, None),
            ("fn choose(c: bool, a: &i64, b: &i64) -> &i64 { if c { return a; } else { return b; } } "
             "fn f(){ let mut x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r = choose(true, a, b); print(*r); x = 3; y = 4; }", 0, None),
            ("fn choose(c: bool, a: &i64, b: &i64) -> &i64 { if c { return a; } else { return b; } } "
             "fn f(){ let x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r = choose(true, a, b); y = 4; print(*r); }", 8, 5),
            ("fn id(r: &mut i64) -> &mut i64 { r } fn f(){ let mut x = 1; let mut r = &mut x; "
             "let mut q = id(r); *q = 2; *r = 3; }", 0, None),
            ("fn id(r: &mut i64) -> &mut i64 { r } fn f(){ let mut x = 1; let mut r = &mut x; "
             "let mut q = id(r); *r = 3; *q = 2; }", 8, 5),
            ("fn f(r: &i64) -> &i64 { r }", 0, None),
            ("fn f(r: &mut i64) -> &mut i64 { return r; }", 0, None),
            ("fn f(r: &i64) -> &mut i64 { return r; }", 8, 1),
            ("fn f() -> &i64 { let x = 1; let r = &x; r }", 8, 4),
            ("fn f() -> &i64 { let x = 1; return &x; }", 8, 4),
            ("fn f(x: i64) -> &i64 { &x }", 8, 4),
            ("fn f(r: &i64) { print(*r); }", 0, None),
            ("fn main(){ let x = 1; let r = &x; print(r); }", 8, 1),
            ("fn f(c: bool) { let mut x = 1; while c { x = 2; } print(x); }", 0, None),
            ("fn f() { let x = 1; while x > 0 { print(x); } }", 0, None),
            ("fn f(c: bool) { let x = 1; while c { break; } print(x); }", 0, None),
            ("fn f(c: bool) { let x = 1; while c { print(x); continue; } }", 0, None),
            ("fn f(c: bool) { let x = 1; while c { drop(x); break; } print(x); }", 8, 6),
            ("fn f(c: bool) { let x = 1; while c { if c { drop(x); break; } else { break; } } print(x); }", 8, 6),
            ("fn f(c: bool) { let x = 1; while c { if c { drop(x); break; } else { continue; } } print(x); }", 8, 6),
            ("fn f(c: bool) { let x = 1; while c { if c { drop(x); break; } print(x); } }", 0, None),
            ("fn f(c: bool) { let x = 1; while c { if c { drop(x); continue; } break; } }", 8, 6),
            ("fn f() { break; }", 8, 6),
            ("fn f(c: bool) { let x = 1; while c { drop(x); } }", 8, 6),
            ("fn main(){ let mut x = 1; let r = &mut x; drop(r); x = 2; }", 0, None),
            ("fn main(){ let x = 1; let r = &x; drop(r); print(*r); }", 8, 4),
            ("fn f(){ let mut x = 1; let r = &mut x; let mut q = r; *q = 2; }", 0, None),
            ("fn f(){ let x = 1; let r = &x; let q = r; print(*r); }", 8, 4),
            ("fn f(){ let x = 1; let r: &i64 = &x; print(*r); }", 0, None),
            ("fn f(){ let x = 1; let r: &i32 = &x; }", 8, 1),
            ("fn f(){ let x = 1; let r = &x; { move r; print(*r); } }", 0, None),
            ("fn f(){ let x = 1; let r = &x; { move r; print(*r); } print(*r); }", 8, 4),
            ("fn main(){ let x = 1; let r = &x; print(*r); }", 0, None),
            ("fn main(){ let x = 1; { let r = &x; print(*r); } drop(x); }", 0, None),
            ("fn main(){ let x = 1; drop(x); let r = &x; }", 8, 4),
            ("fn f(){ let mut p = pool<i64>(2); let a = p.new(3); print(*a); drop(a); }", 0, None),
            ("fn f(){ let mut p = pool<i64>(2); let a = p.new(true); }", 8, 1),
            ("fn f(){ let mut p = pool<i64>(2); let a = p.new(3); drop(a); print(*a); }", 8, 4),
            ("fn f(){ let mut p = pool<i64>(2); let a = p.new(3); let b = a; print(*b); drop(b); }", 0, None),
            ("fn f(){ let mut p = pool<i64>(2); let a = p.new(3); { move a; drop(a); } }", 0, None),
            ("fn f(){ let mut p = pool<i64>(2); let a = p.new(3); let b = a; drop(a); }", 8, 6),
            ("fn f(c: bool) { let x: u8 = if c { 1 } else { 2 }; print(x); }", 0, None),
            ("fn f(c: bool) { let x = if c { true } else { 2 }; }", 8, 1),
            ("fn f(c: bool) { let x = 1; let y = if c { x } else { 2 }; print(x); }", 8, 6),
            ("fn f(c: bool) { let x = 1; if c { drop(x); } print(x); }", 8, 6),
            ("fn f(c: bool) { let x = 1; if c { drop(x); return; } print(x); }", 0, None),
            ("fn f(){ let mut x = 1; let mut r = &mut x; let mut q = &mut *r; "
             "let mut s = &mut *q; *s = 2; *r = 3; }", 0, None),
            ("fn f(){ let mut x = 1; let mut r = &mut x; let mut q = &mut *r; "
             "let mut s = &mut *q; *r = 3; *s = 2; }", 8, 5),
            ("fn f(){ let mut x = 1; let mut r = &mut x; let mut q = &mut *r; *q = 2; *r = 3; }", 0, None),
            ("fn f(){ let mut x = 1; let mut r = &mut x; let mut q = &mut *r; *r = 3; *q = 2; }", 8, 5),
            ("fn f(){ let mut x = 1; let r = &mut x; let q = &mut *r; drop(r); print(*q); }", 8, 5),
            ("fn f(){ let x = 1; let r = &x; let q = &mut *r; }", 8, 5),
            ("fn main(){ let mut x = 1; let r = &mut x; print(*r); }", 0, None),
            ("fn main(){ let mut x = 1; { let mut r = &mut x; *r = 2; } print(x); }", 0, None),
            ("fn main(){ let x = 1; let r = &mut x; }", 8, 5),
            ("fn main(){ let mut x = 1; let r = &mut x; print(*r); x = 2; print(x); }", 0, None),
            ("fn main(){ let mut x = 1; let r = &mut x; x = 2; print(*r); }", 8, 5),
            ("fn main(){ let x = 1; let mut r = &x; *r = 2; }", 8, 5),
        )
        for source, status, rule in checks:
            input_path.write_text(source)
            result = subprocess.run([executable, "--check", input_path], capture_output=True)
            assert result.returncode == status, (source, result)
            if rule is None:
                assert result.stdout == b"", (source, result)
            else:
                actual_rule, offset = map(int, result.stdout.split())
                assert actual_rule == rule and 0 <= offset < len(source), (source, result)
        parity = (
            ("fn first(c: bool, a: &i64, b: &i64) -> &i64 { "
             "if c { return a; } return second(a, b); } "
             "fn second(a: &i64, b: &i64) -> &i64 { first(true, a, b) } "
             "fn main() { let x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r = first(false, a, b); print(*r); y = 3; }", True),
            ("fn relay(c: bool, a: &i64, b: &i64) -> &i64 { "
             "if c { return a; } return relay(true, a, b); } "
             "fn main() { let x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r = relay(false, a, b); print(*r); y = 3; }", True),
            ("fn relay(c: bool, a: &i64, b: &i64) -> &i64 { "
             "if c { return a; } return relay(true, a, b); } "
             "fn main() { let mut x = 1; let y = 2; let a = &x; let b = &y; "
             "let r = relay(false, a, b); x = 3; print(*r); }", False),
            ("fn id(n: i64) -> i64 { n } fn hold(a: &mut i64, n: i64) -> &mut i64 { a } "
             "fn main() { let mut x = 1; let a = &mut x; let r = hold(a, id(copy(x))); print(*r); }", False),

            ("fn id(n: i64) -> i64 { n } fn hold(a: &i64, n: i64) -> &i64 { a } "
             "fn main() { let x = 1; let a = &x; let r = hold(a, id(x)); print(*r); }", False),
            ("fn id(n: i64) -> i64 { n } fn hold(a: &i64, n: i64) -> &i64 { a } "
             "fn main() { let x = 1; let a = &x; let r = hold(a, id(copy(x))); print(*r); }", True),
            ("struct Inner { a: A<i64> } struct Outer { child: Inner } "
             "fn main() { let mut p = pool<i64>(2); let inner = Inner { a: p.new(1) }; "
             "let outer = Outer { child: inner }; drop(outer); }", True),
            ("struct Inner { a: A<i64> } struct Outer { child: Inner } "
             "fn main() { let mut p = pool<i64>(2); let inner = Inner { a: p.new(1) }; "
             "let outer = Outer { child: inner }; drop(inner); }", False),
            ("struct Boxed { value: A<i64> } fn main() { let mut p = pool<i64>(2); "
             "let a = p.new(1); let item = Boxed { value: a }; drop(item); }", True),
            ("struct Boxed { value: A<i64> } fn main() { let mut p = pool<i64>(2); "
             "let a = p.new(1); let item = Boxed { value: a }; drop(a); }", False),
            ("struct Pair { a: A<i64>, b: A<i64> } fn main() { let mut p = pool<i64>(2); "
             "let mut q = pool<i64>(2); let item = Pair { a: p.new(1), b: q.new(2) }; "
             "let moved = item; drop(moved); }", True),
            ("struct Inner { a: A<i64> } struct Outer { child: Inner, b: A<i64> } "
             "fn main() { let mut p = pool<i64>(2); let item = Outer { child: Inner { a: p.new(1) }, "
             "b: p.new(2) }; drop(item); }", True),
            ("struct Pair { a: A<i64>, b: A<i32> } fn main() { let mut p = pool<i64>(2); "
             "let item = Pair { a: p.new(1), b: p.new(2) }; drop(item); }", False),
            ("struct Boxed { value: A<i64> } fn main() { let mut p = pool<i64>(2); "
             "let item = Boxed { value: p.new(1) }; drop(item); }", True),
            ("struct Boxed { value: A<i64> } fn main() { let mut p = pool<i64>(2); "
             "let item = Boxed { value: p.new(1) }; let moved = item; drop(item); }", False),
            ("fn id(a: &mut i64) -> &mut i64 { a } "
             "fn pick(a: &mut i64, b: &mut i64) -> &mut i64 { a } "
             "fn main() { let mut x = 1; let mut y = 2; let a = &mut x; let b = &mut y; "
             "let r = id(a); let q = pick(r, b); print(*q); }", True),
            ("fn id(n: i64) -> i64 { n } fn hold(a: &i64, n: i64) -> &i64 { a } "
             "fn main() { let x = 1; let a = &x; let r = hold(a, id(2)); print(*r); }", True),
            ("fn f(c: bool) { let x = 1; let r = &x; while c { print(*r); } } fn main() {}", True),
            ("fn f(c: bool) { let x = 1; let r = &x; while c { drop(r); continue; } } fn main() {}", False),
            ("fn first(a: &i64, b: &i64) -> &i64 { a } "
             "fn relay(a: &i64, b: &i64) -> &i64 { first(a, b) } "
             "fn main() { let x = 1; let mut y = 2; let a = &x; let b = &y; "
             "let r = relay(a, b); y = 3; print(*r); }", True),
            ("fn first(a: &i64, b: &i64) -> &i64 { a } "
             "fn relay(a: &i64, b: &i64) -> &i64 { first(a, b) } "
             "fn main() { let mut x = 1; let y = 2; let a = &x; let b = &y; "
             "let r = relay(a, b); x = 3; print(*r); }", False),
            ("fn pick(a: &mut i64, b: &mut i64) -> &mut i64 { a } "
             "fn main() { let mut x = 1; let mut y = 2; let a = &mut x; let b = &mut y; "
             "let r = pick(a, b); y = 3; print(*r); }", True),
            ("fn pick(a: &mut i64, b: &mut i64) -> &mut i64 { a } "
             "fn main() { let mut x = 1; let a = &mut x; let r = pick(a, a); print(*r); }", False),
        )
        for source, accepted in parity:
            input_path.write_text(source)
            rust = subprocess.run([FRONTEND, "check"], input=source, text=True, capture_output=True)
            crust = subprocess.run([executable, "--check", input_path], capture_output=True)
            assert (rust.returncode == 0) == accepted, (source, rust.stderr)
            assert crust.returncode == (0 if accepted else 8), (source, crust)
        pool_cleanup = (
            "fn main() { let mut p = pool<i64>(1); "
            "{ let a = p.new(10); let moved = a; print(*moved); } "
            "let b = p.new(20); print(*b); drop(b); let c = p.new(30); print(*c); }"
        )
        aggregate_cleanup = (
            "struct Inner { a: A<i64> } struct Outer { child: Inner, b: A<i64> } "
            "fn main() { let mut p = pool<i64>(1); let mut q = pool<i64>(1); "
            "{ let a = p.new(1); let inner = Inner { a: a }; "
            "let outer = Outer { child: inner, b: q.new(2) }; { move outer; } } "
            "let p1 = p.new(10); let q1 = q.new(20); print(*p1); print(*q1); "
            "let item = Outer { child: Inner { a: p1 }, b: q1 }; drop(item); "
            "let p2 = p.new(30); print(*p2); }"
        )
        custom_cleanup = (
            "struct Leaf { n: i64 } impl Leaf { fn drop(&mut self) { print((*self).n); } } "
            "struct Parent { child: Leaf, n: i64 } "
            "impl Parent { fn drop(&mut self) { print((*self).n); } } "
            "fn main() { let parent = Parent { child: Leaf { n: 20 }, n: 10 }; "
            "let moved = parent; drop(moved); { let child = Leaf { n: 30 }; } }"
        )
        cursor_cleanup = (
            "fn main() { { let mut p = pool<i64>(4096); let a = p.new(10); print(*a); } "
            "{ let mut p = pool<i64>(4096); let a = p.new(20); print(*a); } "
            "let mut p = pool<i64>(4096); let a = p.new(30); print(*a); }"
        )
        ordered_body = (
            "struct Item { a: i64, b: i64, c: i64 } "
            "impl Item { fn drop(&mut self) -> Void { print((*self).b); print((*self).a); print((*self).c); } } "
            "struct Empty {} impl Empty { fn drop(&mut self) {} } "
            "fn main() { let empty = Empty {}; drop(empty); "
            "let item = Item { a: 20, b: 10, c: 30 }; let moved = item; drop(moved); }"
        )
        early_cleanup = (
            "struct Item { n: i64 } impl Item { fn drop(&mut self) { print((*self).n); } } "
            "fn main() { let outer = Item { n: 30 }; "
            "{ let first = Item { n: 10 }; drop(first); let inner = Item { n: 20 }; return; } "
            "let unreachable = Item { n: 40 }; }"
        )
        nominal_cleanup = (
            "struct Item { n: i64 } impl Item { fn drop(&mut self) { print((*self).n); } } "
            "fn main() { let mut pool = pool<Item>(1); "
            "{ let a = pool.new({ n: 10 }); let moved = a; } "
            "let b = pool.new(Item { n: 20 }); drop(b); let c = pool.new({ n: 30 }); }"
        )
        region_cleanup = (
            "fn main() { let mut p = pool<Vector<i64>>(1); "
            "#(stack_region: max_size=1K) { let mut v = p.new(); "
            "v.push(10); v.push(20); print(v[0]); print(v[1]); } "
            "#(stack_region: max_size=2K) { let mut v = p.new(); v.push(30); print(v[0]); } }"
        )
        nested_pooled_cleanup = """struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { child: A<Leaf>, n: i64, other: i64 }
impl Parent { fn drop(&mut self) { print((*self).n); print((*self).other); } }
fn main() {
    let mut leaves = pool<Leaf>(1);
    let mut parents = pool<Parent>(1);
    let leaf = leaves.new({ n: 30 });
    let parent = parents.new({ other: 20, child: leaf, n: 10 });
    let moved = parent;
    drop(moved);
    let leaf2 = leaves.new({});
    let parent2 = parents.new({ child: leaf2, n: 10, other: 20 });
}
"""
        conditional_cleanup = """struct Item { n: i64 }
impl Item { fn drop(&mut self) {
    if (*self).n > 1 { print((*self).n); return; }
    else { print(20); }
    print(30);
} }
fn main() { let a = Item { n: 10 }; drop(a); let b = Item { n: 1 }; }
"""
        region_reuse = """#(datastack: region_stack_size=1K, region_size=1K)
fn main() {
    let mut p = pool<Vector<i64>>(2);
    let mut a = p.new();
    a.push(10);
    print(a[0]);
    drop(a);
    let mut b = p.new();
    b.push(20);
    print(b[0]);
}
"""
        region_transfer = """#(datastack: region_stack_size=1K, region_size=1K)
fn main() {
    let mut p = pool<Vector<i64>>(1);
    let mut result = #(stack_region: max_size=2K, count=1) {
        let mut v = p.new();
        v.push(10);
        v
    };
    print(result[0]);
    result.push(20);
    print(result[1]);
}
"""
        field_order = """struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { left: A<Leaf>, right: A<Leaf>, n: i64 }
impl Parent { fn drop(&mut self) { print((*self).n); } }
fn main() {
    let mut leaves = pool<Leaf>(2);
    let mut parents = pool<Parent>(1);
    let parent = parents.new({ right: leaves.new({ n: 30 }), n: 10, left: leaves.new({ n: 20 }) });
    drop(parent);
}
"""
        partial_defaults = """struct Pair { a: i64, b: i64 }
impl Pair { fn drop(&mut self) { print((*self).a); print((*self).b); } }
fn main() { let mut p = pool<Pair>(1); let v = p.new({a: 20}); drop(v); let w = p.new(); drop(w); }
"""
        loop_cleanup = """struct Item { n: i64 }
impl Item { fn drop(&mut self) {
    while (*self).n > 0 && !false { print((*self).n); break; }
    let mut n = 1;
    { n = 20; }
    print(n);
    print(30);
} }
fn main() { let mut p = pool<Item>(1); let a = p.new({ n: 10 }); drop(a); }
"""
        helper_cleanup = """struct Item { n: i64 }
fn display(n: i64) { print(n); }
fn finished() { print(30); }
impl Item { fn drop(&mut self) { let n = (*self).n; display(copy(n)); print(n); finished(); } }
fn main() { let a = Item { n: 10 }; drop(a); }
"""
        region_count = """#(datastack: size=4K, region_stack_size=1K, region_size=1K)
fn main() {
    let mut p = pool<Vector<i64>>(3);
    #(stack_region: max_size=1K, count=1) {
        let mut a = p.new();
        let mut b = p.new();
        a.push(10);
        b.push(20);
        drop(a);
        let mut c = p.new();
        c.push(30);
        print(b[0]);
        print(c[0]);
    }
}
"""
        region_inferred = """#(datastack: region_stack_size=1K)
fn main() { let mut p = pool<Vector<i64>>(1); let mut v = p.new(); v.push(10); print(v[0]); }
"""
        named_projection = """struct Item { n: i64, unused: i64 }
fn main() {
    let mut p = pool<Item>(1);
    let a = p.new(n: 10, unused: 20);
    print((*a).n); print((*a).unused);
}
"""
        enum_cleanup = """struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
enum Item { Empty, Full { leaf: A<Leaf> } }
fn main() {
    let mut items = pool<Item>(1);
    let mut leaves = pool<Leaf>(1);
    let a = items.new(Item.Empty {});
    let b = items.new(Item.Full { leaf: leaves.new({ n: 10 }) });
    drop(b);
    let c = items.new(Item.Full { leaf: leaves.new({ n: 20 }) });
    drop(c);
    drop(a);
}
"""
        arithmetic_cleanup = """struct Item { n: i64 }
impl Item { fn drop(&mut self) { print((*self).n + 1); print((*self).n * 2); print((*self).n / 2); } }
fn main() { let a = Item { n: 10 }; drop(a); }
"""
        byte_region = (
            "#(datastack: region_stack_size=1K) "
            "fn main() { let mut p = pool<Vector<u8>>(1); let mut v = p.new(); "
            + "v.push(255); " * 130 + "print(v[129]); }"
        )
        direct_region = """#(datastack: region_stack_size=2K, region_size=2K)
fn main() {
    let mut p = pool<Vector<i64>>(1);
    let mut a = #(stack_region: max_size=1K) { p.new() };
    a.push(10); print(a[0]);
}
"""
        pooled_transfer = """struct Point { x: i64 }
impl Point { fn drop(&mut self) { print((*self).x); } }
fn main() {
    let mut p = pool<Point>(1);
    let point = { let original = p.new({ x: 10 }); original };
    drop(point);
    let next = { p.new({ x: 20 }) };
    drop(next);
}
"""
        dynamic_region = """fn main() {
    let mut pool = pool<Vector<i64>>(1);
    let mut values = pool.new();
    let mut index: i64 = 0;
    while index < 3 { values.push(copy(index)); index = index + 1; }
    print(values.len());
}
"""
        scalar_fields = """
struct Item { n: i32, flag: bool }
impl Item { fn drop(&mut self) { print((*self).n); print((*self).flag); } }
fn main() {
    let mut p = pool<Item>(1);
    let a = p.new(n: 10, flag: true);
    drop(a);
    drop(Item { n: 20, flag: false });
}
"""
        nested_defaults = """
struct Inner { n: i64 }
impl Inner { fn drop(&mut self) { print((*self).n); } }
struct Item { x: Inner, y: Inner }
impl Item { fn drop(&mut self) { print((*self).x.n); } }
fn main() {
    let mut p = pool<Item>(1);
    let a = p.new({ x: Inner { n: 10 } });
    drop(a);
    drop(Item { x: Inner { n: 20 }, y: Inner { n: 30 } });
}
"""
        local_destructor_pool = """
struct Item { n: i64 }
impl Item { fn drop(&mut self) {
    let mut p = pool<i64>(1);
    let a = p.new((*self).n);
    print(*a);
} }
fn main() { drop(Item { n: 10 }); drop(Item { n: 20 }); }
"""
        adopt_named = """
struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { child: A<Leaf>, n: i64 }
impl Parent { fn drop(&mut self) { print((*self).n); } }
fn main() {
    let mut leaves = pool<Leaf>(1);
    let mut parents = pool<Parent>(1);
    let temp = Parent { child: leaves.new({ n: 20 }), n: 10 };
    let a = parents.new(temp);
    print((*a).n);
    drop(a);
    let next = leaves.new({ n: 30 });
    drop(next);
}
"""
        pooled_nested_escape = """
struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { child: Leaf }
fn main() {
    let mut p = pool<Parent>(1);
    let out = { p.new({ child: Leaf { n: 7 } }) };
    let other = Leaf { n: 9 };
    drop(out);
    drop(other);
}
"""
        async_drop = """
struct Leaf { n: i64 }
impl Leaf { fn drop(&mut self) { print((*self).n); } }
struct Parent { first: Leaf, last: Leaf }
impl Parent { fn drop(&mut self) { print((*self).first.n); } }
async fn run(parent: Parent, last: Leaf) {
    yield;
    drop(last);
    yield;
}
fn main() {
    let h = runtime::spawn(run(Parent { first: Leaf { n: 2 }, last: Leaf { n: 3 } },
                              Leaf { n: 1 }));
    drop(h.join());
}
"""
        integer_pool_fields = """
struct Limits { min: i64, hex: i64 }
impl Limits { fn drop(&mut self) { print((*self).min); print((*self).hex); } }
fn main() {
    let mut p = pool<Limits>(1);
    let value: A<Limits> = p.new({ min: -9223372036854775808, hex: 0xFF });
    drop(value);
}
"""
        cases = [(program, b"10\n20\n30\n") for program in (
            pool_cleanup, aggregate_cleanup, custom_cleanup, cursor_cleanup,
            ordered_body, early_cleanup, nominal_cleanup, region_cleanup, conditional_cleanup, loop_cleanup,
        )] + [
            (nested_pooled_cleanup, b"10\n20\n30\n10\n20\n0\n"),
            (region_reuse, b"10\n20\n"),
            (region_transfer, b"10\n20\n"),
            (field_order, b"10\n30\n20\n"),
            (partial_defaults, b"20\n0\n0\n0\n"),
            (helper_cleanup, b"10\n10\n30\n"),
            (region_count, b"20\n30\n"),
            (region_inferred, b"10\n"),
            (named_projection, b"10\n20\n"),
            (enum_cleanup, b"10\n20\n"),
            (arithmetic_cleanup, b"11\n20\n5\n"),
            (byte_region, b"255\n"),
            (direct_region, b"10\n"),
            (pooled_transfer, b"10\n20\n"),
            (dynamic_region, b"3\n"),
            (scalar_fields, b"10\ntrue\n20\nfalse\n"),
            (nested_defaults, b"10\n0\n10\n20\n30\n20\n"),
            (local_destructor_pool, b"10\n20\n"),
            (adopt_named, b"10\n10\n20\n30\n"),
            (RUST_DROP_INLINE, b"1\n2\n3\n4\n"),
            (RUST_DROP_POOLED, b"1\n2\n3\n4\n"),
            (integer_pool_fields, b"-9223372036854775808\n255\n"),
            (pooled_nested_escape, b"7\n9\n"),
        ]
        for program, expected in cases:
            input_path.write_text(program)
            subprocess.run([executable, "--check", input_path], check=True)
            generated = work / "cleanup.c"
            output = subprocess.check_output([executable, "--emit-c", input_path])
            generated.write_bytes(output)
            cleanup = work / "cleanup"
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                 "-fno-sanitize-recover=all", generated, "-o", cleanup], check=True,
            )
            rust_cleanup = work / "rust-cleanup"
            subprocess.run([FRONTEND, "build", "-o", rust_cleanup],
                           input=program, text=True, check=True)
            assert subprocess.check_output([cleanup]) == subprocess.check_output([rust_cleanup]) == expected
        input_path.write_text("fn main() { let mut p = pool<i64>(1); let a = p.new(10); drop(a); drop(a); }")
        emit = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
        assert emit.returncode == 8 and b"#include" not in emit.stdout, emit
        unsigned_pool = "fn main() { let mut p = pool<u64>(1); let a = p.new(10); drop(a); }"
        input_path.write_text(unsigned_pool)
        emit = subprocess.run([executable, "--emit-c", input_path], capture_output=True, check=True)
        generated.write_bytes(emit.stdout)
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        generated, "-o", cleanup], check=True)
        assert subprocess.check_output([cleanup]) == b""
        input_path.write_text(
            "struct Item { n: i64 } impl Item { fn drop(&self) { print((*self).n); } } "
            "fn main() { let item = Item { n: 10 }; drop(item); }"
        )
        emit = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
        assert emit.returncode == 8 and b"#include" not in emit.stdout, emit
        input_path.write_text(
            "struct Item { n: i64 } impl Item { fn drop(&mut self) { print((*self).missing); } } "
            "fn main() {}"
        )
        for mode in ("--check", "--emit-c"):
            emit = subprocess.run([executable, mode, input_path], capture_output=True)
            assert emit.returncode == 8 and b"#include" not in emit.stdout, emit
        region_escape = (
            "fn main() { let v = { let mut p = pool<Vector<i64>>(1); "
            "let local = p.new(); local }; drop(v); }"
        )
        input_path.write_text(region_escape)
        emitted = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
        reference = subprocess.run([FRONTEND, "check"], input=region_escape, text=True, capture_output=True)
        assert emitted.returncode == 8 and reference.returncode != 0 and b"#include" not in emitted.stdout
        moved_destructor_binding = helper_cleanup.replace("display(copy(n))", "display(n)")
        input_path.write_text(moved_destructor_binding)
        emitted = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
        reference = subprocess.run([FRONTEND, "check"], input=moved_destructor_binding, text=True, capture_output=True)
        assert emitted.returncode != 0 and reference.returncode != 0 and b"#include" not in emitted.stdout
        partial_nominal = (
            "struct Pair { a: i64, b: i64 } fn main() { let v = Pair { a: 20 }; drop(v); }",
            "struct S {} struct T {} fn main() { let mut p = pool<S>(1); let v: A<T> = p.new(); drop(v); }",
            "enum E { V { a: i64 } } fn main() { let mut p = pool<E>(1); let v = p.new(E.V {}); drop(v); }",
            "struct S { a: A<i64> } fn main() { let mut p = pool<S>(1); "
            "let v = { let mut q = pool<i64>(1); p.new({ a: q.new(10) }) }; drop(v); }",
        )
        for program in partial_nominal:
            input_path.write_text(program)
            emitted = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
            reference = subprocess.run([FRONTEND, "check"], input=program, text=True, capture_output=True)
            assert emitted.returncode == 8 and reference.returncode != 0 and b"#include" not in emitted.stdout
        async_cases = (
            (RUST_DROP_ASYNC, b"8\n", b"8\n"),
            (async_drop, b"1\n2\n2\n3\n", b"1\n2\n3\n2\n"),
            (RUST_DROP_ASYNC.replace("drop(h.join());", ""), b"8\n", b"8\n"),
        )
        failed_launch = work / "fail-launch.c"
        failed_launch.write_text("""
#include <pthread.h>
int deny_launch(pthread_t *thread, const pthread_attr_t *attr,
                void *(*entry)(void *), void *arg) {
    (void)thread; (void)attr; (void)entry; (void)arg;
    return 11;
}
""")
        for program, expected, failure_cleanup in async_cases:
            input_path.write_text(program)
            subprocess.run([executable, "--check", input_path], check=True)
            generated.write_bytes(subprocess.check_output([executable, "--emit-c", input_path]))
            subprocess.run([FRONTEND, "build", "-o", rust_cleanup],
                           input=program, text=True, check=True)
            reference = subprocess.run([rust_cleanup], capture_output=True, timeout=10, check=True)
            assert reference.stdout == expected, reference
            rust_source = work / "rust-async.c"
            rust_source.write_text(subprocess.check_output([FRONTEND, "emit-c"], input=program, text=True))
            subprocess.run(["cc", "-std=c11", "-pthread", "-Dpthread_create=deny_launch",
                            rust_source, failed_launch, "-lm", "-o", rust_cleanup], check=True)
            reference_failure = subprocess.run([rust_cleanup], capture_output=True, timeout=10, check=True)
            assert (reference_failure.stdout, reference_failure.stderr) == (failure_cleanup, b""), reference_failure
            for optimization in ("-O0", "-O2"):
                args = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization,
                        "-pthread", "-fsanitize=undefined", "-fno-sanitize-recover=all", generated]
                subprocess.run([*args, "-o", cleanup], check=True)
                actual = subprocess.run([cleanup], capture_output=True, timeout=10, check=True)
                assert (actual.stdout, actual.stderr) == (reference.stdout, reference.stderr), actual
                subprocess.run([*args, "-Dpthread_create=deny_launch", failed_launch, "-o", cleanup], check=True)
                failed = subprocess.run([cleanup], capture_output=True, timeout=10, check=True)
                assert (failed.stdout, failed.stderr) == (failure_cleanup, b""), failed
        duplicate_join = RUST_DROP_ASYNC.replace("drop(h.join());", "drop(h.join()); drop(h.join());")
        input_path.write_text(duplicate_join)
        refused = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
        reference_refusal = subprocess.run([FRONTEND, "check"], input=duplicate_join, text=True, capture_output=True)
        assert refused.returncode == 8 and b"#include" not in refused.stdout, refused
        assert reference_refusal.returncode != 0, reference_refusal
        print(f"{len(async_cases)} async destructor traces matched under UBSan, including injected launch failure cleanup")
        overflow = (
            "fn main() { let mut p = pool<Vector<i64>>(1); "
            "#(stack_region: max_size=1K) { let mut v = p.new(); "
            + "v.push(1); " * 129 + "} }"
        )
        transfer_overflow = direct_region.replace("a.push(10); print(a[0]);", "a.push(10); " * 129)
        dynamic_overflow = direct_region.replace(
            "a.push(10); print(a[0]);",
            "let mut i: i64 = 0; while i < 129 { a.push(copy(i)); i = i + 1; }",
        )
        for program, expected in (
            (overflow, b""),
            (region_reuse.replace("drop(a);", ""), b"10\n"),
            (transfer_overflow, b""),
            (dynamic_overflow, b""),
        ):
            input_path.write_text(program)
            generated.write_bytes(subprocess.check_output([executable, "--emit-c", input_path]))
            subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                 "-fno-sanitize-recover=all", generated, "-o", cleanup], check=True,
            )
            subprocess.run([FRONTEND, "build", "-o", rust_cleanup],
                           input=program, text=True, check=True)
            for binary in (cleanup, rust_cleanup):
                result = subprocess.run([binary], capture_output=True, timeout=10)
                assert result.returncode != 0 and result.stdout == expected, result
        print(f"{len(cases)} generated execution traces, four region limits compared against Rust, nine emission refusals")
        regional_cases = [(name, source, expected.encode(), 0) for name, source, expected, _ in RUST_REGION_ACCEPTED]
        regional_cases += [(name, source, b"", 1) for name, source in RUST_REGION_EXHAUSTED]
        for name, program, expected, status in regional_cases:
            input_path.write_text(program)
            emitted = subprocess.run([executable, "--emit-c", input_path], capture_output=True)
            assert emitted.returncode == 0, (name, emitted)
            generated.write_bytes(emitted.stdout)
            if name.startswith("a recursive callee") or name.startswith("an unbounded loop"):
                allocation_calls = [line for line in emitted.stdout.splitlines() if line.startswith(b"region_new(r")]
                assert any(line.endswith(b",1);") for line in allocation_calls), name
                assert any(line.endswith(b",0);") for line in allocation_calls), name
            subprocess.run([FRONTEND, "build", "-o", rust_cleanup], input=program, text=True, check=True)
            reference = subprocess.run([rust_cleanup], capture_output=True, timeout=10)
            assert (reference.returncode, reference.stdout) == (status, expected), (name, reference)
            for optimization in ("-O0", "-O2"):
                subprocess.run(
                    ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", optimization, "-fsanitize=undefined",
                     "-fno-sanitize-recover=all", generated, "-o", cleanup], check=True,
                )
                actual = subprocess.run([cleanup], capture_output=True, timeout=10)
                assert (actual.returncode, actual.stdout, actual.stderr) == (
                    reference.returncode, reference.stdout, reference.stderr,
                ), (name, optimization, actual, reference)
        print(f"{len(regional_cases)} Rust region cases matched under UBSan at -O0 and -O2")
        print(f"{len(parity)} rule verdict comparisons against Rust")
        print(f"{len(checks)} rule checker witnesses")
        for length, status in ((131072, 0), (131073, 4)):
            input_path.write_text(" " * length)
            result = subprocess.run([executable, input_path], capture_output=True)
            assert result.returncode == status, result
        input_path.write_bytes(b"// invalid UTF-8: \xff\nfn f() {}")
        result = subprocess.run([executable, input_path], capture_output=True)
        assert (result.returncode, result.stdout, result.stderr) == (3, b"", b"")
        print(f"{len(VALID) + len(corpus)} AST and static graph comparisons, {len(INVALID)} syntax refusals, two size boundaries")


if __name__ == "__main__":
    main()
