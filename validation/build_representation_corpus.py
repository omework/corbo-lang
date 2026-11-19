"""Inventory source witnesses and project parser output into a static graph.

Only syntax is parsed. No Crust checker, code generator or program is run.
"""

import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'prototype'))
sys.path.insert(0, str(ROOT / 'scripts'))
from compiler_location import compiler_root

from crust import Error, Node, Parser


FENCE = re.compile(r'^ *(?P<mark>`{3,}|~{3,})(?P<tag>[\w-]*)[^\n]*\n', re.MULTILINE)
CODE = re.compile(r'\b(?:fn\s+\w+\s*\(|let\s+(?:mut\s+)?\w+\s*[:=]|'
                  r'(?:match|while)\s+[^\n]+\{|runtime::|pool<)|#\((?:directive|type|branch|lock)\b')
NAME = re.compile(r'[A-Za-z_]\w*')
NODE_FLAGS = ('mutable', 'mutable_parameters', 'handle_parameters', 'handle_result',
              'annotation', 'move_import', 'region_limit', 'foreign', 'type_annotations',
              'type_contract', 'branch_wait', 'lock_contract', 'native_block', 'terminated')


def markdown_snippets(path):
    source = path.read_text()
    position = 0
    while match := FENCE.search(source, position):
        closing = re.compile(r'^ *' + re.escape(match['mark'][0]) + r'{'
                             + str(len(match['mark'])) + r',} *$', re.MULTILINE)
        end = closing.search(source, match.end())
        if end is None:
            break
        position = end.end()
        if source[:match.start()].rstrip().endswith('<!-- corpus: rust-only -->'):
            continue
        body = dedent(source[match.end():end.start()])
        if match['tag'] in ('crust', 'rust') or match['tag'] in ('', 'text') and CODE.search(body):
            yield source.count('\n', 0, match.end()) + 1, body


def python_snippets(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in sorted(ast.walk(tree), key=lambda node: (getattr(node, 'lineno', 0), getattr(node, 'col_offset', 0))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and CODE.search(node.value):
            yield node.lineno, dedent(node.value)


def candidates():
    for path in sorted(ROOT.rglob('*.md')):
        if path.name.endswith('-fr.md') or set(path.relative_to(ROOT).parts) & {'.git', 'build', '__pycache__'}:
            continue
        for line, text in markdown_snippets(path):
            yield path, line, 'markdown', text
    for directory in ('src', 'validation'):
        for path in sorted((compiler_root() / directory).rglob('*.crb')):
            yield path, 1, 'source', path.read_text()
    for directory in ('examples', 'validation'):
        for path in sorted((ROOT / directory).rglob('*.crb')):
            yield path, 1, 'source', path.read_text()
    for path in sorted((ROOT / 'tests').rglob('*.py')):
        for line, text in python_snippets(path):
            yield path, line, 'littéral Python', text


def tracked(method, role):
    def parse(self, *args, **kwargs):
        start = self.i
        value = method(self, *args, **kwargs)
        if self.i > start:
            self.spans.append((start, self.i, role, value))
        return value
    return parse


class RepresentationParser(Parser):
    def __init__(self, source):
        super().__init__(source)
        self.spans = []

    statement = tracked(Parser.statement, 'opération')
    block = tracked(Parser.block, 'scope')
    expr = tracked(Parser.expr, 'expression')
    primary = tracked(Parser.primary, 'primaire')
    function = tracked(Parser.function, 'fonction')
    foreign_function = tracked(Parser.foreign_function, 'fonction externe')
    enum = tracked(Parser.enum, 'enum')
    implementation = tracked(Parser.implementation, 'implémentation')
    annotated_function = tracked(Parser.annotated_function, 'contrat de branche')
    syntax_pattern = tracked(Parser.syntax_pattern, 'motif')
    type_annotation = tracked(Parser.type_annotation, 'contrat de type')
    type_argument = tracked(Parser.type_argument, 'type')
    async_pool_directive = tracked(Parser.async_pool_directive, 'directive')
    region_annotation = tracked(Parser.region_annotation, 'directive de région')


def normalize(value, identities, objects, line_offset):
    if isinstance(value, (Node, tuple, list, dict, set, frozenset)):
        identity = id(value)
        if identity in identities:
            return identities[identity]
        index = len(objects)
        identities[identity] = index
        objects.append(None)
        if isinstance(value, Node):
            record = {'op': value.op, 'ligne': value.line - line_offset,
                      'args': normalize(value.args, identities, objects, line_offset)}
            for name in NODE_FLAGS:
                flag = getattr(value, name)
                if flag is not None and (flag is False and name in ('lock_contract', 'branch_wait') or flag):
                    record[name] = normalize(flag, identities, objects, line_offset)
        elif isinstance(value, dict):
            record = {'table': [[key, normalize(item, identities, objects, line_offset)]
                                for key, item in value.items()]}
        else:
            items = sorted(value, key=repr) if isinstance(value, (set, frozenset)) else value
            record = {'forme': type(value).__name__, 'éléments': [
                normalize(item, identities, objects, line_offset) for item in items]}
        objects[index] = record
        return index
    if isinstance(value, bytes):
        return {'octets_hex': value.hex()}
    return {'valeur': value}


def token_role(token, context):
    if token == ';':
        return 'séparation ou absence de résultat'
    if token in ('{', '}'):
        return 'frontière de scope ou délimitation de déclaration'
    if token in ('if', 'else', 'match', '=>', 'while', 'loop', 'return', 'break', 'continue', 'yield'):
        return 'contrôle ou point de sortie'
    if token in ('move', 'let', 'mut', '&', '*', '=', '+=', '-=', '*=', '/=', '%='):
        return 'liaison, capacité ou opération selon le nœud'
    if token in ('(', ')', ',', '<', '>', '[', ']', ':', '.', '->', '..'):
        return 'structure du nœud ou des opérandes'
    if NAME.fullmatch(token):
        return 'nom, membre, type ou mot réservé'
    if context == 'motif':
        return 'discriminant ou liaison de motif'
    return 'valeur, opérateur ou marqueur'


def execution_facts(tree, identities, scopes):
    scope_by_tree = {scope['arbre']: scope for scope in scopes}
    facts = []

    def link(value):
        return identities.get(id(value), value if isinstance(value, (str, int, bool)) else None)

    def emit(kind, node, scope, **fields):
        ident = len(facts)
        facts.append({'id': ident, 'sorte': kind, 'nœud': link(node), 'scope': scope, **fields})
        return ident

    def bind(node, name, env, scope, **fields):
        binding = emit('liaison', node, scope, nom=name, **fields)
        env[name] = binding
        return binding

    def visit_match(subject, arms, env, scope, function, loops):
        visit(subject, env, scope, function, loops)
        for pattern, body in arms:
            inner_scope = scope_by_tree.get(link(body), {}).get('id', scope)
            local = env.copy()
            if pattern[0] == 'variant':
                for field, name in pattern[3]:
                    if name != '_':
                        bind(pattern, name, local, inner_scope, champ=field, sujet=link(subject))
            elif pattern[0] == 'pattern_call' and pattern[2][0] == 'pattern_name':
                bind(pattern, pattern[2][1], local, inner_scope, sujet=link(subject))
            emit('bras', pattern, inner_scope, sujet=link(subject), corps=link(body))
            visit(body, local, inner_scope, function, loops)

    def visit(value, env, scope, function=None, loops=()):
        if isinstance(value, Node):
            op, args = value.op, value.args
            if op in ('fn', 'async_fn'):
                name, parameters, result, body = args
                inner_scope = scope_by_tree.get(link(body), {}).get('id', scope)
                local = {}
                emit('fonction', value, scope, nom=name, corps=inner_scope, résultat=list(result), asynchrone=op == 'async_fn')
                for parameter, mode, typ in parameters:
                    bind(value, parameter, local, inner_scope, mode=mode, type=typ,
                         mutable=parameter in value.mutable_parameters)
                visit(body, local, inner_scope, link(value))
                return
            if op == 'var':
                name, initializer = args
                visit(initializer, env, scope, function, loops)
                bind(value, name, env, scope, type=value.annotation, mutable=value.mutable, valeur=link(initializer))
                return
            if op == 'syntax_match':
                emit('contrôle', value, scope, opération=op)
                visit_match(*args, env, scope, function, loops)
                return
            if op in ('loop', 'while'):
                body = args[0]
                emit('boucle', value, scope, opération=op, corps=link(body))
                visit(body, env, scope, function, (*loops, link(value)))
                return
            if value.move_import:
                name = args[0]
                source = env.get(name)
                destination = bind(value, name, env, scope)
                emit('déplacement', value, scope, source=source, destination=destination, nom=name)
                return
            if op in ('return', 'break', 'continue', 'yield', 'if_yield', 'match_yield', 'while_check'):
                destination = function if op == 'return' else loops[-1] if loops and op in ('break', 'continue') else None
                point = emit('contrôle', value, scope, opération=op, destination=destination,
                             valeur=link(args[0]) if args else None)
                if op in ('return', 'break', 'continue'):
                    scopes[scope]['sorties'].append({'sorte': op, 'point': point})
            if op in ('assign', 'syntax_assignment'):
                emit('écriture', value, scope, place=link(args[:-1]), résultat_droite=link(args[-1]))
            visit(args, env, scope, function, loops)
        elif isinstance(value, (list, tuple)):
            context = scope_by_tree.get(link(value))
            if context is not None and scope != context['id']:
                scope, env = context['id'], env.copy()
            if isinstance(value, tuple) and value and isinstance(value[0], str):
                op = value[0]
                if op == 'name':
                    emit('usage', value, scope, nom=value[1], liaison=env.get(value[1]))
                    return
                if op in ('ref', 'mut', 'ref_expr', 'mut_expr'):
                    target = value[1]
                    emit('référence', value, scope, mode='mutable' if op.startswith('mut') else 'partagé',
                         cible=link(target), nom=target if isinstance(target, str) else None,
                         liaison=env.get(target) if isinstance(target, str) else None)
                if op == 'source' and value[1] == 'pool':
                    emit('pool', value, scope, type=value[3], capacité=value[2])
                if op in ('array_literal', 'array_repeat', 'array_hashmap_new', 'new_enum'):
                    emit('collection', value, scope, constructeur=op, contenu=link(value))
                if op == 'method_call' and value[2] == 'new':
                    emit('adresse candidate', value, scope, source=link(value[1]), initialisation=link(value[3]))
                if op in ('call', 'method_call', 'closure_apply'):
                    name = value[1] if op == 'call' else None
                    emit('appel', value, scope, nom=name, liaison=env.get(name), opérandes=link(value))
                if op in ('array_index', 'field', 'syntax_deref', 'array_slice', 'utf8_slice_place'):
                    emit('projection', value, scope, opération=op, base=link(value[1]))
                if op in ('await', 'task_spawn', 'syntax_match', 'if_expr', 'loop_expr'):
                    emit('contrôle', value, scope, opération=op, opérandes=link(value))
                if op == 'closure_literal':
                    _, moving, parameters, result, body, _ = value
                    inner_scope = scope_by_tree.get(link(body), {}).get('id', scope)
                    closure = emit('closure', value, scope, corps=inner_scope, move=moving, résultat=result)
                    local = env.copy()
                    for name, typ, mutable in parameters:
                        bind(value, name, local, inner_scope, type=typ, mutable=mutable)
                    first = len(facts)
                    visit(body, local, inner_scope, link(value))
                    outer_bindings = set(env.values())
                    captures = {fact['liaison']: fact['nom'] for fact in facts[first:]
                                if fact['sorte'] in ('usage', 'référence', 'appel') and fact.get('liaison') in outer_bindings
                                and 'nom' in fact}
                    for source, name in captures.items():
                        emit('capture', value, scope, closure=closure, source=source, nom=name,
                             mode='déplacement' if moving else None)
                    return
                if op == 'syntax_match':
                    visit_match(*value[1:], env, scope, function, loops)
                    return
            for item in value:
                visit(item, env, scope, function, loops)

    visit(tree, {}, 0)
    return facts


def graph_spans(parser, identities):
    scopes = [span for span in parser.spans if span[2] == 'scope']
    spans = [(first, last, kind, identities[id(value)])
             for first, last, kind, value in parser.spans if id(value) in identities]
    # The parser inserts the while test in a new list ahead of the parsed body.
    # Recover the iteration scope from the block span before that rewrite.
    for first, last, kind, value in parser.spans:
        if not isinstance(value, Node) or value.op != 'while' or id(value) not in identities:
            continue
        body = value.args[0]
        matches = [(begin, end) for begin, end, _, block in scopes
                   if first < begin and end == last and len(block) == len(body) - 1
                   and all(a is b for a, b in zip(block, body[1:]))]
        if matches:
            spans.append((first, last, 'scope', identities[id(body)]))
    return sorted(set(spans), key=lambda span: (span[0], -span[1], span[2], span[3]))


def build_graph(parser, tree, offset=0, prefix=0, suffix=0):
    identities, objects = {}, []
    root = normalize(tree, identities, objects, offset)
    source_tokens = parser.tokens[:-1]
    start, stop = prefix, len(source_tokens) - suffix
    spans = graph_spans(parser, identities)
    scopes = [{'id': 0, 'parent': None, 'entrée': None, 'plage': [0, stop - start], 'arbre': root}]
    scope_stack = [(start, stop, 0)]
    for first, last, kind, node in spans:
        if kind != 'scope' or first < start or last > stop:
            continue
        while len(scope_stack) > 1 and not (scope_stack[-1][0] <= first and last <= scope_stack[-1][1]):
            scope_stack.pop()
        ident = len(scopes)
        scopes.append({'id': ident, 'parent': scope_stack[-1][2], 'entrée': first - start,
                       'plage': [first - start, last - start], 'arbre': node})
        scope_stack.append((first, last, ident))

    for scope in scopes:
        scope['enfants'] = []
        scope['sorties'] = [{'sorte': 'fin de bloc', 'frontière': scope['plage'][1]}]
        scope['repères_datastack'] = None
    for scope in scopes[1:]:
        scopes[scope['parent']]['enfants'].append(scope['id'])
    facts = execution_facts(tree, identities, scopes)
    facts_by_node = defaultdict(list)
    for fact in facts:
        facts_by_node[fact['nœud']].append(fact['id'])
    tokens = []
    for index in range(start, stop):
        token, line = source_tokens[index]
        covering = sorted((last - first, kind, node) for first, last, kind, node in spans
                          if first <= index < last)
        context = covering[0][1] if covering else 'programme'
        scope = next(scope['id'] for scope in reversed(scopes)
                     if scope['plage'][0] <= index - start < scope['plage'][1])
        nodes = list(dict.fromkeys(node for _, _, node in covering)) or [root]
        tokens.append({'index': index - start, 'ligne': line - offset, 'lexème': token,
                       'rôle': token_role(token, context), 'scope': scope,
                       'nœuds': nodes, 'faits': [fact for node in nodes for fact in facts_by_node[node]]})
    return {'racine': root, 'objets': objects, 'scopes': scopes, 'faits': facts, 'tokens': tokens}


def reconstruct(source, kind):
    parser = RepresentationParser(source)
    try:
        tree = parser.parse_syntax()
    except Error as error:
        if kind == 'source':
            return {'statut': 'hors syntaxe actuelle', 'diagnostic': str(error)}
        signature = re.search(r'\bfn\s+\w+\s*\([^{}]*\)(?:\s*->\s*[^{};\n]+)?\s*$', source)
        if signature and not re.search(r'\bextern\b', source):
            header = RepresentationParser(source + '\n{}')
            try:
                tree = header.parse_syntax()
            except Error:
                pass
            else:
                return {'statut': 'fragment de signature', **build_graph(header, tree, suffix=2)}
        if re.match(r'\s*(?:async\s+fn|fn|extern|struct|enum|impl)\b', source):
            return {'statut': 'hors syntaxe actuelle', 'diagnostic': str(error)}
        fragment = RepresentationParser('fn corpus_fragment() {\n' + source + '\n}')
        try:
            tree = fragment.parse_syntax()
        except Error:
            return {'statut': 'fragment non reconnu', 'diagnostic': str(error)}
        return {'statut': 'fragment de bloc', **build_graph(fragment, tree, offset=1, prefix=5, suffix=1)}
    if not tree:
        return {'statut': 'vide'}
    return {'statut': 'programme ou déclarations', **build_graph(parser, tree)}


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'build' / 'representation_corpus.jsonl'
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    token_counts = Counter()
    graphs = {}
    with output.open('w', encoding='utf-8') as stream:
        for path, line, kind, source in candidates():
            key = kind == 'source', source
            if key not in graphs:
                graphs[key] = reconstruct(source, kind)
            graph = graphs[key]
            status = graph['statut']
            counts[kind, status] += 1
            token_counts[kind] += len(graph.get('tokens', ()))
            record = {'fichier': (str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else 'corboc/' + str(path.relative_to(compiler_root()))), 'ligne_source': line, 'origine': kind, **graph}
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
    for (kind, status), count in sorted(counts.items()):
        print(f'{kind}\t{status}\t{count}')
    for kind, count in sorted(token_counts.items()):
        print(f'{kind}\ttokens représentés\t{count}')
    print(output)


if __name__ == '__main__':
    main()
