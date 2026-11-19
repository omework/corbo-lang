"""Small independent oracle: enumerate routes to typed pool parameters.

It consumes an explicit call graph, not a Crust AST, compiler summary or C code.
A route relates storage parameters; the endpoints carry declared requirements.
"""
import random


def generate_graph(seed):
    rng = random.Random(seed)
    other = 'Int' if seed % 2 == 0 else 'Message'
    declarations = {(0, 0): 'Int', (1, 0): other}
    calls = {0: [], 1: []}
    for function in range(2, 7):
        calls[function] = []
        for callee in rng.sample(range(function), min(function, 2)):
            route = list(range(3))
            rng.shuffle(route)
            calls[function].append((callee, tuple(route)))
    # Ensure every graph contains a transitive, reordered terminal obligation.
    calls[6].append((5, (2, 0, 1)))
    return declarations, calls


def obligations(declarations, calls):
    # Enumerate complete paths instead of reusing recursively inferred summaries.
    result = {}
    for function in calls:
        for parameter in range(3):
            pending, reached = [(function, parameter)], set()
            types = set()
            while pending:
                node = pending.pop()
                if node in reached:
                    continue
                reached.add(node)
                if node in declarations:
                    types.add(declarations[node])
                owner, actual = node
                for callee, mapping in calls[owner]:
                    pending.extend((callee, formal) for formal in range(3) if mapping[formal] == actual)
            result[function, parameter] = frozenset(types)
    return result


def render_graph(declarations, calls):
    code = ['enum Message { Empty {} }']
    for function in calls:
        parameters = ', '.join(f'p{i}: &Pool<{declarations[function, i]}>'
                              if (function, i) in declarations else f'p{i}: &Allocator'
                              for i in range(3))
        body = ' '.join(f'f{callee}(' + ', '.join(f'p{i}' for i in mapping) + ');'
                        for callee, mapping in calls[function])
        code.append(f'fn f{function}({parameters}) {{ {body} }}')
    return ' '.join(code)


def render_caller(types):
    return 'fn main() { ' + ' '.join(f'let mut p{i} = pool<{typ}>(1);' for i, typ in enumerate(types)) + \
           ' f6(&p0, &p1, &p2); }'
