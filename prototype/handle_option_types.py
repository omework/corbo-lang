"""Static type of the optional handle returned by Vector<A<T>>.pop."""
import re


def local_option_element(typ):
    match = re.fullmatch(r'Option<([A-Za-z_][A-Za-z_0-9:]*)>', typ or '')
    if match and match[1] not in ('Int', 'u8', 'Bool', 'bool', 'char', 'Void', 'String'):
        return match[1]
    return None


def option_type(element, storage="pool"):
    return f'Option<{element}>' if storage == "local" else f'Option<A<{element}>>'


def option_element(typ):
    if isinstance(typ, str) and typ.startswith('Option<A<') and typ.endswith('>>'):
        return typ[len('Option<A<'):-2]
    return None


def option_storage(typ):
    while typ.startswith('Result<') and typ.endswith(',runtime::Error>'):
        typ = typ[len('Result<'):-len(',runtime::Error>')]
    if local_option_element(typ) is not None:
        return 'local'
    if option_element(typ) is not None:
        return 'pool'
    return None
