"""Compare generated UTF-8 runtime code with Python's encoder."""

import random
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from crust import compile_source


class Utf8RuntimeTests(unittest.TestCase):
    def test_decode_positions_and_roundtrip_against_python_encoding(self):
        compiler = shutil.which("clang") or shutil.which("cc")
        if compiler is None:
            self.skipTest("C compiler unavailable")

        rng = random.Random(1439)
        scalars = [
            0, 0x7f, 0x80, 0x7ff, 0x800, 0xd7ff, 0xe000, 0xffff,
            0x10000, 0x10ffff, ord("e"), 0x301,
        ]
        scalars.extend(value for value in rng.sample(range(0x110000), 512)
                       if not 0xd800 <= value <= 0xdfff)
        encoded = [chr(value).encode("utf-8") for value in scalars]
        bytes_c = ", ".join(str(byte) for chunk in encoded for byte in chunk)
        boundaries = [0]
        for chunk in encoded[:12]:
            boundaries.append(boundaries[-1] + len(chunk))
        boundaries_c = ", ".join(map(str, boundaries))
        cases_c = ", ".join(f"{{{value}, {len(chunk)}}}"
                            for value, chunk in zip(scalars, encoded))

        # Exercise generated C directly with independently calculated offsets
        # and widths, including pointer identity for slices.
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = f"""
#include <assert.h>
int main(void) {{
    static const unsigned char bytes[] = {{{bytes_c}}};
    static const struct {{ uint32_t scalar; int width; }} cases[] = {{{cases_c}}};
    CrustText text = {{bytes, sizeof bytes}};
    static const int boundaries[] = {{{boundaries_c}}};
    CrustText prefix = {{bytes, boundaries[sizeof boundaries / sizeof boundaries[0] - 1]}};
    for (size_t lo = 0; lo < sizeof boundaries / sizeof boundaries[0]; ++lo) {{
        CrustText tail = text_slice(prefix, boundaries[lo], 0, 0);
        assert(tail.bytes == bytes + boundaries[lo]);
        assert(tail.length == prefix.length - (size_t)boundaries[lo]);
        for (size_t hi = lo; hi < sizeof boundaries / sizeof boundaries[0]; ++hi) {{
            CrustText part = text_slice(prefix, boundaries[lo], boundaries[hi], 1);
            assert(part.bytes == bytes + boundaries[lo]);
            assert(part.length == (size_t)(boundaries[hi] - boundaries[lo]));
        }}
    }}
    int offset = 0;
    assert(text_char_at(text, -1).status == CRUST_CHAR_OUT_OF_BOUNDS);
    assert(text_char_at(text, sizeof bytes).status == CRUST_CHAR_OUT_OF_BOUNDS);
    assert(text_char_at((CrustText){{bytes, 0}}, 0).status == CRUST_CHAR_OUT_OF_BOUNDS);
    assert(char_from_text((CrustText){{bytes, 0}}).status == CRUST_CHAR_EMPTY);
    assert(char_from_text(text).status == CRUST_CHAR_MULTIPLE);
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i) {{
        CrustCharResult indexed = text_char_at(text, offset);
        assert(indexed.status == CRUST_CHAR_OK && indexed.value == cases[i].scalar);
        CrustCharResult isolated = char_from_text((CrustText){{bytes + offset, cases[i].width}});
        assert(isolated.status == CRUST_CHAR_OK && isolated.value == indexed.value);
        assert(char_utf8_len(indexed.value) == cases[i].width);
        for (int j = 1; j < cases[i].width; ++j) {{
            assert(text_char_at(text, offset + j).status == CRUST_CHAR_NOT_BOUNDARY);
        }}
        char_print(indexed.value);
        offset += cases[i].width;
    }}
    assert((size_t)offset == sizeof bytes);
    return 0;
}}
"""
        expected = b"".join(chunk + b"\n" for chunk in encoded)
        with tempfile.TemporaryDirectory() as folder:
            c_path = Path(folder) / "utf8.c"
            executable = Path(folder) / "utf8"
            c_path.write_text(emitted + harness)
            for opt in ("-O0", "-O2"):
                with self.subTest(opt=opt):
                    build = subprocess.run(
                        [compiler, "-std=c11", opt, "-fsanitize=undefined",
                         "-fno-sanitize-recover=all", str(c_path), "-o", str(executable)],
                        capture_output=True, timeout=30,
                    )
                    self.assertEqual(build.returncode, 0, build.stderr)
                    run = subprocess.run([str(executable)], capture_output=True, timeout=10)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stderr, b"")
                    self.assertEqual(run.stdout, expected)

    def test_validation_agrees_with_python_on_raw_bytes(self):
        compiler = shutil.which("clang") or shutil.which("cc")
        if compiler is None:
            self.skipTest("C compiler unavailable")

        def valid(data):
            try:
                data.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                return 0
            return 1

        # One bit per pair keeps exhaustive coverage of two-byte input
        # compact. Additional cases target the longer encoding boundaries.
        pairs = bytearray(8192)
        for n in range(65536):
            pairs[n // 8] |= valid(n.to_bytes(2, "big")) << (n % 8)
        rng = random.Random(2671)
        cases = [
            b"", b"\0", b"\x80", b"\xc0\x80", b"\xe0\x9f\xbf",
            b"\xe0\xa0\x80", b"\xed\x9f\xbf", b"\xed\xa0\x80",
            b"\xf0\x8f\xbf\xbf", b"\xf0\x90\x80\x80",
            b"\xf4\x8f\xbf\xbf", b"\xf4\x90\x80\x80",
            b"\xf5\x80\x80\x80", b"a\xc2", b"a\xe2\x82", b"a\xf0\x9f\x8c",
            b"\xc2a", b"\xe2\x82a", b"\xf0\x9f\x8ca", "a🌍\0été".encode(),
        ]
        cases.extend(bytes(rng.randrange(256) for _ in range(rng.randrange(1, 9)))
                     for _ in range(1024))
        bytes_c = ", ".join(str(value) for value in pairs)
        cases_c = ", ".join(
            "{{" + ", ".join(map(str, data or b"\0")) + f"}}, {len(data)}, {valid(data)}}}"
            for data in cases
        )
        emitted = compile_source("").replace("int main(void)", "int crust_entry(void)")
        harness = f"""
#include <assert.h>
int main(void) {{
    static const unsigned char expected[] = {{{bytes_c}}};
    static const struct {{ unsigned char data[16]; size_t length; int valid; }} cases[] = {{{cases_c}}};
    static const unsigned char four_bytes[] = {{0xf0, 0x90, 0x80, 0x80}};
    for (size_t length = 1; length < sizeof four_bytes; ++length) {{
        assert(!text_validate_utf8(four_bytes, length));
    }}
    for (unsigned int n = 0; n < 65536; ++n) {{
        unsigned char pair[] = {{n >> 8, n & 0xff}};
        assert(text_validate_utf8(pair, sizeof pair) == ((expected[n / 8] >> (n % 8)) & 1));
        unsigned char reversed[] = {{pair[1], pair[0]}};
        CrustTextResult result = text_from_vector_slice((VectorSlice){{reversed, sizeof reversed, 1}});
        assert((result.status == 0) == ((expected[n / 8] >> (n % 8)) & 1));
        if (result.status == 0) {{
            assert(text_byte_address(result.text, 0) == reversed + 1);
            assert(text_byte_address(result.text, 1) == reversed);
        }}
    }}
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i) {{
        assert(text_validate_utf8(cases[i].data, cases[i].length) == cases[i].valid);
        unsigned char reversed[16];
        for (size_t j = 0; j < cases[i].length; ++j)
            reversed[j] = cases[i].data[cases[i].length - j - 1];
        CrustTextResult descending = text_from_vector_slice((VectorSlice){{reversed, cases[i].length, 1}});
        assert((descending.status == 0) == cases[i].valid);
        CrustTextResult result = text_from_utf8(cases[i].data, cases[i].length);
        assert((result.status == 0) == cases[i].valid);
        if (result.status == 0) {{
            CrustText view = text_result_value(result);
            assert(view.bytes == cases[i].data && view.length == cases[i].length);
        }} else {{
            assert(result.text.bytes == NULL && result.text.length == 0);
        }}
    }}
    return 0;
}}
"""
        with tempfile.TemporaryDirectory() as folder:
            c_path = Path(folder) / "validate.c"
            executable = Path(folder) / "validate"
            c_path.write_text(emitted + harness)
            for opt in ("-O0", "-O2"):
                with self.subTest(opt=opt):
                    build = subprocess.run(
                        [compiler, "-std=c11", opt, "-fsanitize=undefined",
                         "-fno-sanitize-recover=all", str(c_path), "-o", str(executable)],
                        capture_output=True, timeout=30,
                    )
                    self.assertEqual(build.returncode, 0, build.stderr)
                    run = subprocess.run([str(executable)], capture_output=True, timeout=10)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stderr, b"")
