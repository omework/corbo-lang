"""Types of the two ownership results produced by handle-vector operations."""


def exchange_type(element, optional=False, storage="pool"):
    handle = element if storage == "local" else f'A<{element}>'
    return f'Result<{"()" if optional else handle},{handle}>'


def exchange_element(typ):
    if not isinstance(typ, str) or not typ.startswith('Result<') or not typ.endswith('>'):
        return None
    body = typ[7:-1]
    depth = 0
    for index, character in enumerate(body):
        if character == '<':
            depth += 1
        elif character == '>':
            depth -= 1
        elif character == ',' and depth == 0:
            first, second = body[:index], body[index + 1:]
            if second.startswith('A<') and second.endswith('>') and first in ('()', second):
                return second[2:-1]
            from handle_option_types import local_option_element
            if first in ('()', second) and local_option_element(f'Option<{second}>') is not None:
                return second
            return None
    return None


def exchange_optional(typ):
    return exchange_element(typ) is not None and typ.startswith('Result<(),')


def exchange_storage(typ):
    while typ.startswith('Result<') and typ.endswith(',runtime::Error>'):
        typ = typ[len('Result<'):-len(',runtime::Error>')]
    element = exchange_element(typ)
    if element is None:
        return None
    return 'pool' if typ.endswith(',A<' + element + '>>') else 'local'
