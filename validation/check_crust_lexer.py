"""Compare raw tokens and lexical errors before either frontend parses."""
import argparse
from pathlib import Path
import random
import subprocess
import tempfile

from check_crust_bootstrap import FRONTEND, INVALID, PACKAGE, ROOT, VALID

DIAGNOSTICS = (
    "caractère inattendu",
    "entier hexadécimal sans chiffres",
    "caractère de contrôle dans un texte",
    "échappement inconnu",
    "échappement Unicode invalide",
    "surrogate isolé",
    "paire UTF-16 incomplète",
    "paire UTF-16 invalide",
    "opérande assembleur non fermé",
    "nom d’opérande assembleur invalide",
    "bloc assembleur non fermé",
    "texte non fermé",
)

LEXICAL_CASES = (
    "", " \t\r\n\f", "a\x0bb", "a\x00b", "a\xa0b", "a\u200bb",
    "a é", "_ _a A_1 $ d", "a// é", "//é\rhidden\nnext",
    '0 001 0xFF 0Xb 0xfg 7. .7 1..3 ...5 1...5 1.2.3 1e3 1.4e-3',
    '0x', '0Xz', '0x.5', 'a 0x\n',
    '{}()[]<>,:;.#=+-*/%&|^!~@ :: -> => .. == != <= && || << += -= *= /= %= >= >>',
    'Vector<Vector<i64>>=x x>>=y x<==y x<<=y x&=y x|=y x^=y',
    '"é 😀" "\\\"\\\\\\/\\b\\f\\n\\r\\t" "\\u00e9\\u0000\\uD83D\\uDE00"',
    '"\\uD7FF\\uE000\\uFFFF" "\\uD800\\uDC00\\uDBFF\\uDFFF"',
    '"\\uD800"', '"\\uD800\\u"', '"\\uD800\\u00"', '"\\uD800\\u0041"',
    '"\\uDC00"', '"\\uZZZZ"', '"\\u00é0"', '"\\q"', '"\\', '"é\n"', '"\x00"', '"é',
    '@as @{ @asmx { } @asm // comment\n{}',
    '@asm { // } ${invalid name}\r still comment\n mov ${_x9}, ${y} }+1',
    '@asm { ${first}${second} }', '@asm { ${} }', '@asm { ${9x} }',
    '@asm { ${é} }', '@asm { ${a b} }', '@asm { ${abc', '@asm { ${a b',
    '@asm { ${x}', '@asm { // }', '@asm { mov a, b',
    '@asm\u200b{}', '#(if: target.os == "other" { $ })',
) + tuple(
    f'@asm{space}{{ ${{left}} }}'
    for space in ('\t', '\v', '\f', '\r\n', '\u0085', '\u00a0', '\u1680',
                  '\u2000', '\u200a', '\u2028', '\u2029', '\u202f', '\u205f', '\u3000')
)


def generated_cases():
    # Compose tokens with and without a separating space to exercise maximal
    # munch, comments, generic closers and incomplete multi-byte constructs.
    seed = random.Random(20261114)
    parts = (
        "let", "A", "_", "fn", "x9", "true", ">>", ">=", "..", ".", ".9", "1.",
        "0x", "0Xff", "9", "<", "+=", "/", "//tail", "\r\n", "\v", "\f",
        '"é"', '"\\uD800\\uDC00"', '"\\uD800', '@asm { ${x} }', '@asm',
        '{', '}', '$', '\u00a0', 'é', '"',
    )
    for index in range(384):
        length = seed.randint(1, 12)
        yield f"generated {index}", "".join(
            seed.choice(parts) + seed.choice(("", "", " ", "\n")) for _ in range(length)
        ).encode()


def inputs():
    for index, source in enumerate((*LEXICAL_CASES, *VALID, *INVALID)):
        yield f"fixture {index}", source.encode()
    for directory in (PACKAGE, ROOT / "examples", ROOT / "validation", ROOT / "stdlib"):
        for path in sorted(directory.rglob("*.crb")):
            yield str(path.relative_to(ROOT)), path.read_bytes()
    yield from generated_cases()
    yield "maximum token density", b";" * 131072
    yield "maximum input with assembly tail", b" " * (131072 - 13) + b"@asm { ${x} }"


def compare(bootstrap, work):
    cases = list(inputs())
    requests = b"".join(b"lex\t" + source.hex().encode() + b"\n" for _, source in cases)
    reference = subprocess.run([FRONTEND, "--batch"], input=requests, capture_output=True, check=True)
    outcomes = reference.stdout.decode().splitlines()
    assert len(outcomes) == len(cases), reference.stderr
    path = work / "input.crb"
    accepted = rejected = 0
    for (name, source), expected in zip(cases, outcomes):
        path.write_bytes(source)
        run = subprocess.run([bootstrap, "--lex", path], capture_output=True, timeout=15)
        assert not run.stderr, (name, run.stderr)
        status, data = expected.split("\t", 1)
        if run.returncode == 0:
            values = run.stdout.decode().splitlines()
            assert len(values) % 3 == 0, (name, values)
            observed = ",".join(":".join(values[i:i + 3]) for i in range(0, len(values), 3))
            assert status == "OK" and data == observed, (name, source[:120], expected[:200], observed[:200])
            accepted += 1
        else:
            assert status == "ERR" and run.returncode == 3, (name, source[:120], expected[:200], run)
            code, offset = map(int, run.stdout.splitlines())
            assert 1 <= code <= len(DIAGNOSTICS), (name, code)
            assert data == f"{offset}\t{DIAGNOSTICS[code - 1]}", (name, source[:120], expected, code, offset)
            rejected += 1
    # File decoding and capacity errors sit outside the raw UTF-8 lexer API.
    malformed = (b"\xff", b"//\xc0\xaf", b'"\xed\xa0\x80"', b"//\xf4\x90\x80\x80", b"//\xe2\x82")
    for source in malformed:
        path.write_bytes(source)
        run = subprocess.run([bootstrap, "--lex", path], capture_output=True, timeout=15)
        assert (run.returncode, run.stdout, run.stderr) == (3, b"", b""), run
    path.write_bytes(b" " * 131073)
    run = subprocess.run([bootstrap, "--lex", path], capture_output=True, timeout=15)
    assert (run.returncode, run.stdout, run.stderr) == (4, b"", b""), run
    print(f"{accepted} token streams and {rejected} lexical diagnostics matched Rust")
    print(f"{len(malformed)} malformed UTF-8 files refused and the 128 KiB boundary checked")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path, help="run an existing bootstrap executable")
    options = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        bootstrap = options.bootstrap
        if bootstrap is None:
            src = work / "bootstrap.c"
            bootstrap = work / "bootstrap"
            with src.open("w") as output:
                subprocess.run([FRONTEND, "emit-c", PACKAGE], stdout=output, check=True)
            subprocess.run(
                ["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                 "-fno-sanitize-recover=all", src, "-o", bootstrap], check=True,
            )
        compare(bootstrap.resolve(), work)


if __name__ == "__main__":
    main()
