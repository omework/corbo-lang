"""Primitive formats, constant evaluation, and checked C arithmetic."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import math


@dataclass(frozen=True)
class Format:
    mode: str
    c_type: str
    bits: int
    signed: bool = False
    precision: int = 0
    exponent: int = 0

    @property
    def lower(self):
        return -(1 << (self.bits - 1)) if self.signed else 0

    @property
    def upper(self):
        return (1 << (self.bits - self.signed)) - 1


FORMATS = {
    'i32': Format('scalar', 'int32_t', 32, True),
    'i64': Format('i64', 'int64_t', 64, True),
    'u8': Format('byte', 'uint8_t', 8),
    'u16': Format('u16', 'uint16_t', 16),
    'u32': Format('u32', 'uint32_t', 32),
    'u64': Format('u64', 'uint64_t', 64),
    'f32': Format('f32', 'float', 32, True, 24, 127),
    'f64': Format('f64', 'double', 64, True, 53, 1023),
}
MODE_TYPES = {spec.mode: name for name, spec in FORMATS.items()}
EXTRA_MODES = {mode: typ for mode, typ in MODE_TYPES.items() if mode not in ('scalar', 'byte')}
EXTRA_C_TYPES = {mode: FORMATS[typ].c_type for mode, typ in EXTRA_MODES.items()}
NUMERIC_REFERENCE_FIELDS = {
    (mode, typ): f'{mode}_{typ}_reference'
    for typ in EXTRA_C_TYPES for mode in ('ref', 'mut')
}
NUMERIC_REFERENCE_SIGNATURES = {field: signature for signature, field in NUMERIC_REFERENCE_FIELDS.items()}
NUMERIC_JOIN_FIELDS = {f'join_{mode}': f'{mode}_value' for mode in EXTRA_MODES}
NUMERIC_JOIN_C = '    union {\n' + ''.join(
    f'        {ctype} {NUMERIC_JOIN_FIELDS["join_" + mode]};\n'
    for mode, ctype in EXTRA_C_TYPES.items()
) + '    };\n'
INTEGER_MODES = frozenset(mode for mode, typ in MODE_TYPES.items() if not FORMATS[typ].precision)
SHIFT = {'<<': 'L', '>>': 'R'}
CONVERSION_PAYLOADS = {f'numeric_conversion_{typ}': typ for typ in FORMATS}
CONVERSION_C_TYPES = {mode: f'CrustConversion_{typ}' for mode, typ in CONVERSION_PAYLOADS.items()}
CONVERSION_FAMILIES = {mode: 24 + index for index, mode in enumerate(CONVERSION_PAYLOADS)}


def conversion_mode(typ):
    return f'numeric_conversion_{typ}'


def conversion_type(typ):
    return f'Result<{("Int" if typ == "i32" else typ)},NumericConversionError>'


class NumericError(ValueError):
    pass


def numeric_type(typ):
    if typ == 'Int':
        return 'i32'
    return typ if typ in FORMATS else None


def exact_cast(source, target):
    a, b = FORMATS[source], FORMATS[target]
    if a.precision:
        return b.precision >= a.precision and b.exponent >= a.exponent
    if b.precision:
        return a.bits - a.signed <= b.precision
    return b.lower <= a.lower and a.upper <= b.upper


def checked_integer(value, typ, *, literal=False):
    spec = FORMATS[typ]
    if not spec.lower <= value <= spec.upper:
        if literal:
            raise NumericError(f'littéral entier hors des bornes de {typ}')
        raise NumericError(f'débordement arithmétique {typ}')
    return value


def round_float(value, typ, *, negative_zero=False):
    """Round an exact rational to a binary format without rounding via double."""
    spec = FORMATS[typ]
    if not value:
        return -0.0 if negative_zero else 0.0
    magnitude = abs(value)
    numerator, denominator = magnitude.numerator, magnitude.denominator
    exponent = numerator.bit_length() - denominator.bit_length()
    power = Fraction(2) ** exponent
    if magnitude < power:
        exponent -= 1
    quantum = max(exponent, 1 - spec.exponent) - (spec.precision - 1)
    scaled = magnitude / (Fraction(2) ** quantum)
    units, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2 * remainder > scaled.denominator or (2 * remainder == scaled.denominator and units % 2):
        units += 1
    if not units:
        raise NumericError(f'résultat flottant non nul arrondi à zéro ({typ})')
    if units.bit_length() - 1 + quantum > spec.exponent:
        raise NumericError(f'débordement flottant {typ}')
    result = math.ldexp(float(units), quantum)
    return -result if value < 0 else result


def literal_value(raw, typ):
    if FORMATS[typ].precision:
        return round_float(Fraction(Decimal(raw)), typ, negative_zero=raw.startswith('-'))
    return checked_integer(raw, typ, literal=True)


def evaluate(op, typ, left, right=0):
    spec = FORMATS[typ]
    if op in ('/', '%') and right == 0:
        raise NumericError('division par zéro')
    if spec.precision:
        if op == 'neg':
            return -left
        a, b = Fraction(left), Fraction(right)
        result = {'+': lambda: a + b, '-': lambda: a - b,
                  '*': lambda: a * b, '/': lambda: a / b}[op]()
        if result:
            return round_float(result, typ)
        # The exact zero case can still carry the IEEE sign.
        return {'+': lambda: left + right, '-': lambda: left - right,
                '*': lambda: left * right, '/': lambda: left / right}[op]()
    if op in SHIFT:
        if not 0 <= right < spec.bits:
            raise NumericError(f'nombre de positions hors limites pour {typ}')
        result = left << right if op == '<<' else left >> right
    elif op in ('/', '%'):
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        result = quotient if op == '/' else left - quotient * right
    elif op == '~':
        result = ~left if spec.signed else spec.upper ^ left
    else:
        result = {'+': lambda: left + right, '-': lambda: left - right,
                  '*': lambda: left * right, '&': lambda: left & right,
                  '|': lambda: left | right, '^': lambda: left ^ right,
                  'neg': lambda: -left}[op]()
    return checked_integer(result, typ)


def c_literal(typ, value):
    spec = FORMATS[typ]
    if spec.precision:
        return value.hex() + ('f' if typ == 'f32' else '')
    if typ == 'i32':
        return str(value)
    if typ == 'i64':
        return 'INT64_MIN' if value == spec.lower else f'INT64_C({value})'
    return f'(({spec.c_type})UINT64_C({value}))'


def c_operation(op, typ, left, right='0'):
    spec = FORMATS[typ]
    if op == 'neg' and spec.precision:
        return f'-({left})'
    if spec.precision:
        return f"crust_{typ}_arithmetic('{op}', {left}, {right})"
    code = SHIFT.get(op, 'N' if op == 'neg' else op)
    return (f"({spec.c_type})crust_integer_arithmetic('{code}', {left}, {right}, "
            f'{spec.bits}, {int(spec.signed)})')


def c_print(mode, value):
    spec = FORMATS[MODE_TYPES[mode]]
    if spec.precision:
        digits = 9 if spec.bits == 32 else 17
        return f'printf("%.{digits}g\\n", (double)({value}));'
    code, cast = ('lld', 'long long') if spec.signed else ('llu', 'unsigned long long')
    return f'printf("%{code}\\n", ({cast})({value}));'


def c_conversion(source, target, value, result, *, declare=True):
    """Emit a conversion check before any out-of-range C cast."""
    src, dst = FORMATS[source], FORMATS[target]
    result_type = CONVERSION_C_TYPES[conversion_mode(target)]
    lines = [f'{result_type} {result} = {{13, 0}};' if declare else
             f'{result} = ({result_type}){{13, 0}};']
    store = f'{result}.value = ({dst.c_type})({value});'
    success = f'{result}.status = 0;'
    if dst.precision:
        if not src.precision:
            # Even a rounded UINT64_MAX is at most 2**64, safe in __int128.
            lines.extend((store, f'if ((__int128){result}.value == (__int128)({value})) {success}'))
        else:
            maximum = 'FLT_MAX' if target == 'f32' else 'DBL_MAX'
            lines.append(f'if (({value}) >= -{maximum} && ({value}) <= {maximum}) {{')
            lines.extend((store, f'if ((double){result}.value == (double)({value})) {success}', '}'))
    else:
        limit = f'((__int128)1 << {dst.bits - dst.signed})'
        lower = f'-{limit}' if dst.signed else '0'
        check = (f'(double)({value}) >= (double)({lower}) && (double)({value}) < (double){limit}'
                 if src.precision else
                 f'(__int128)({value}) >= {lower} && (__int128)({value}) < {limit}')
        lines.append(f'if ({check}) {{')
        if src.precision:
            lines.append(f'if ((double)(__int128)({value}) == (double)({value})) {{')
        lines.extend((store, success, '}'))
        if src.precision:
            lines.append('}')
    return lines


CONVERSION_LAYOUTS = '\n'.join(
    f'typedef struct {{ int status; {FORMATS[typ].c_type} value; }} {CONVERSION_C_TYPES[mode]};'
    for mode, typ in CONVERSION_PAYLOADS.items()
)


RUNTIME = r'''
#include <float.h>
#include <math.h>

_Static_assert(FLT_RADIX == 2 && FLT_MANT_DIG == 24 && FLT_MAX_EXP == 128 &&
               DBL_MANT_DIG == 53 && DBL_MAX_EXP == 1024, "Crust requires binary32 and binary64");

static size_t crust_numeric_index(__int128 index, size_t length) {
    if (index < 0 || index >= (__int128)length) fail("indice hors limites du tableau");
    return (size_t)index;
}

static __int128 crust_integer_arithmetic(char op, __int128 a, __int128 b,
                                         unsigned width, int signed_type) {
    __int128 limit = (__int128)1 << (width - signed_type);
    __int128 lower = signed_type ? -limit : 0;
    __int128 upper = limit - 1;
    __int128 result;
    if ((op == '/' || op == '%') && b == 0) fail("division par zéro");
    if ((op == 'L' || op == 'R') && (b < 0 || b >= width))
        fail("nombre de positions hors limites");
    switch (op) {
        case '+': result = a + b; break;
        case '-': result = a - b; break;
        case '*':
            if (!signed_type) {
                if (b && a > upper / b) fail("débordement arithmétique");
            }
            result = a * b;
            break;
        case '/': result = a / b; break;
        case '%': result = a % b; break;
        case 'N': result = -a; break;
        case '~': result = signed_type ? ~a : upper ^ a; break;
        case '&': result = a & b; break;
        case '|': result = a | b; break;
        case '^': result = a ^ b; break;
        case 'L': result = a * ((__int128)1 << b); break;
        case 'R': {
            __int128 divisor = (__int128)1 << b;
            result = a / divisor;
            if (a < 0 && a % divisor) --result;
            break;
        }
        default: fail("opérateur entier inconnu"); return 0;
    }
    if (result < lower || result > upper) fail("débordement arithmétique");
    return result;
}

#define CRUST_FLOAT_ARITHMETIC(ctype, name)                                  \
static ctype name(char op, ctype a, ctype b) {                                \
    volatile ctype result;                                                   \
    int nonzero;                                                             \
    switch (op) {                                                            \
        case '+': result = a + b; nonzero = a != -b; break;                    \
        case '-': result = a - b; nonzero = a != b; break;                     \
        case '*': result = a * b; nonzero = a != 0 && b != 0; break;            \
        case '/':                                                            \
            if (b == 0) fail("division par zéro");                             \
            result = a / b; nonzero = a != 0; break;                           \
        default: fail("opérateur flottant inconnu"); return 0;                \
    }                                                                        \
    if (!isfinite(result)) fail("débordement flottant");                      \
    if (result == 0 && nonzero) fail("résultat flottant non nul arrondi à zéro"); \
    return result;                                                           \
}
CRUST_FLOAT_ARITHMETIC(float, crust_f32_arithmetic)
CRUST_FLOAT_ARITHMETIC(double, crust_f64_arithmetic)
#undef CRUST_FLOAT_ARITHMETIC
'''
