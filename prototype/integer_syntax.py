"""Exact integer conversions for the prototype's implemented integer types."""

INTEGER_TYPES = {
    'Int': ('scalar', -(2 ** 31), 2 ** 31 - 1),
    'u8': ('byte', 0, 255),
}


def exact_integer_conversion(mode, target):
    source = next((typ for typ, spec in INTEGER_TYPES.items() if spec[0] == mode), None)
    if source is None or target not in INTEGER_TYPES:
        return None, 'as exige deux types entiers pris en charge (Int ou u8)'
    _, lower, upper = INTEGER_TYPES[source]
    result_mode, target_lower, target_upper = INTEGER_TYPES[target]
    if lower < target_lower or upper > target_upper:
        return None, f'conversion {source} as {target} non exacte pour le type source ; utiliser try_from'
    return result_mode, None
