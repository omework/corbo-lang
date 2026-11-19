#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Focused native Gzip/Zstandard interoperability, bounds and malformed-frame checks."""
import argparse
import ctypes
import ctypes.util
import gzip
import os
from pathlib import Path
import random
import shlex
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]


def declaration(name, data):
    # Keep large repeating fixtures small in the language source as well.
    if len(data) > 4096 and data == bytes(range(64)) * (len(data) // 64):
        return (f'let mut {name}:[u8;{len(data)}]=[0;{len(data)}];'
                'let pattern:[u8;64]=[' + ','.join(map(str, range(64))) + '];'
                f'let mut fill:u64=0;while fill<{len(data)}{{{name}[fill]=pattern[fill%64];fill=fill+1;}}\n')
    return f'let {name}:[u8;{len(data)}]=[' + ','.join(map(str, data)) + '];\n'


class Zstd:
    def __init__(self):
        self.lib = ctypes.CDLL(ctypes.util.find_library('zstd'))
        self.lib.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
        self.lib.ZSTD_compressBound.restype = ctypes.c_size_t
        for name in ('ZSTD_compress', 'ZSTD_decompress'):
            fn = getattr(self.lib, name)
            fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
            if name == 'ZSTD_compress':
                fn.argtypes.append(ctypes.c_int)
            fn.restype = ctypes.c_size_t
        self.lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
        self.lib.ZSTD_isError.restype = ctypes.c_uint

    def compress(self, data, level=3):
        output = ctypes.create_string_buffer(self.lib.ZSTD_compressBound(len(data)))
        n = self.lib.ZSTD_compress(output, len(output), data, len(data), level)
        assert not self.lib.ZSTD_isError(n)
        return output.raw[:n]

    def decompress(self, data, capacity):
        output = ctypes.create_string_buffer(max(capacity, 1))
        n = self.lib.ZSTD_decompress(output, capacity, data, len(data))
        assert not self.lib.ZSTD_isError(n), ('reference Zstd rejected native frame', n, data.hex())
        return output.raw[:n]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corboc', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--runner', default='')
    parser.add_argument('--keep', type=Path)
    parser.add_argument('--only', choices=['gzip', 'zstd'])
    parser.add_argument('--encode-only', action='store_true')
    args = parser.parse_args()
    reference = Zstd()
    rng = random.Random(8878)
    samples = [b'', b'a', bytes(range(256)), b'abcd' * 500,
               bytes(rng.randrange(256) for _ in range(2048)), bytes(range(64)) * 4096]
    with tempfile.TemporaryDirectory(prefix='corbo-compression-') as temporary:
        root = args.keep.resolve() if args.keep else Path(temporary)
        (root / 'src').mkdir(parents=True, exist_ok=True)
        (root / 'package.toml').write_text('[package]\nname="compression_test"\n')

        def execute(label, source):
            (root / 'src/main.crb').write_text(source)
            result = subprocess.run([args.corboc.resolve(), '--emit-package-c', root,
                                     '--stdlib-dir', ROOT / 'stdlib/src'],
                                    capture_output=True, timeout=180)
            assert result.returncode == 0 and result.stdout.startswith(b'#'), (label, result.returncode, result.stdout[:300], result.stderr)
            generated = root / f'{label}.c'
            generated.write_bytes(result.stdout)
            binary = root / f'{label}.exe'
            subprocess.run([*shlex.split(args.cc), '-std=c11', '-pthread', '-O2',
                            '-fsanitize=undefined', '-fno-sanitize-recover=all', generated,
                            '-lm', '-o', binary], check=True, timeout=180)
            run = subprocess.run([*shlex.split(args.runner), binary], capture_output=True, timeout=120)
            assert run.returncode == 0 and not run.stderr, (label, run.returncode, run.stdout[:300], run.stderr)
            return [int(line) for line in run.stdout.splitlines()]

        for module, levels in [('gzip', [0, 1, 6, 9]), ('zstd', [0, 1, 3, 10, 22])]:
            if args.only and module != args.only:
                continue
            code = [f'use std::compression::{module};\nfn main()->i32{{\n']
            expected = []
            native_frames = []
            for index, data in enumerate(samples):
                for level in levels:
                    size = len(data); capacity = size * 2 + 1024
                    code.append('{\n' + declaration('input', data))
                    code.append(f'let mut output:[u8;{capacity}]=[0;{capacity}];let mut workspace:[u64;36864]=[0;36864];')
                    fields = f'level:{level}' + (',checksum:true' if module == 'zstd' else '')
                    code.append(f'let params={module}::Params{{{fields}}};')
                    code.append(f'let count=match {module}::compress(&input[..],&mut output[..],&params,&mut workspace[..]){{Ok(v)=>{{v}},Err(e)=>{{drop(e);return 1;}}}};')
                    code.append('print(count);let mut i:u64=0;while i<count as u64{print(output[i]);i=i+1;}\n}\n')
                    expected.append((data, level))
            code.append('0\n}')
            values = execute(module + '_encode', ''.join(code))
            at = 0
            for original, level in expected:
                size = values[at]; at += 1
                compressed = bytes(values[at:at + size]); at += size
                decoded = gzip.decompress(compressed) if module == 'gzip' else reference.decompress(compressed, len(original))
                assert decoded == original
                if level == levels[0]:
                    native_frames.append((original, compressed))
                if len(original) >= 2000 and original.startswith(b'abcd') and not (module == 'gzip' and level == 0):
                    assert len(compressed) < len(original), (module, 'no actual compression')
            assert at == len(values)
            print(f'{module}: {len(expected)} native encodings accepted by reference decoder', flush=True)
            if args.encode_only:
                continue

            fixtures = [(data, gzip.compress(data, mtime=0) if module == 'gzip' else reference.compress(data)) for data in samples]
            if module == 'gzip':
                data = bytes(range(64)) * 32
                for strategy in (zlib.Z_FIXED, zlib.Z_DEFAULT_STRATEGY, zlib.Z_HUFFMAN_ONLY):
                    encoder = zlib.compressobj(6, zlib.DEFLATED, 31, 8, strategy)
                    fixtures.append((data, encoder.compress(data) + encoder.flush()))
                fixtures.append((b'onetwo', gzip.compress(b'one', mtime=0) + gzip.compress(b'two', mtime=0)))
                # Exercise all optional Gzip header fields and their CRC.
                original = gzip.compress(b'header', mtime=0)
                header = original[:3] + bytes([30]) + original[4:10] + b'\x03\x00abcname\x00comment\x00'
                header += (zlib.crc32(header) & 65535).to_bytes(2, 'little')
                fixtures.append((b'header', header + original[10:]))
            else:
                for level in (1, 10, 19):
                    fixtures.append((samples[-1], reference.compress(samples[-1], level)))
                fixtures.append((b'onetwo', reference.compress(b'one') + reference.compress(b'two')))
                skip = bytes.fromhex('502a4d1803000000') + b'abc'
                fixtures.append((b'after', skip + reference.compress(b'after')))
                fixtures.extend(native_frames)
                weighted = bytes(rng.choices(b'aaaaaaaaaaaaabbbbbcccddefghijklmnopqrstuvwxyz', k=4096))
                for level in (1, 3, 19):
                    fixtures.append((weighted, reference.compress(weighted, level)))
                fixtures.append((b'a' * 10, bytes.fromhex('28b52ffd200a53000061')))
                fixtures.append((b'abc', bytes.fromhex('28b52ffd0000190000616263')))
            code = [f'use std::compression::{module};\nfn main()->i32{{\n']
            for fixture_index, (original, compressed) in enumerate(fixtures):
                oracle = gzip.decompress(compressed) if module == 'gzip' else reference.decompress(compressed, len(original))
                assert oracle == original, (module, fixture_index, 'invalid fixture')
                size = len(original)
                code.append('{\n' + declaration('encoded', compressed) + declaration('expected', original))
                code.append(f'let mut output:[u8;{size + 1}]=[90;{size + 1}];')
                workspace = ''
                if module == 'zstd':
                    code.append('let mut workspace:[u8;131072]=[0;131072];')
                    workspace = ',&mut workspace[..]'
                code.append(f'let count=match {module}::decompress(&encoded[..],&mut output[0..{size}]{workspace}){{Ok(v)=>{{v}},Err(e)=>{{drop(e);return {20 + fixture_index};}}}};')
                code.append(f'if count!={size}||output[{size}]!=90{{return 3;}}let view=&output[..count];if !view.content_eq(&expected[..]){{return 4;}}\n}}\n')
            code.append('0\n}')
            assert execute(module + '_decode', ''.join(code)) == []
            print(f'{module}: {len(fixtures)} decoding fixtures passed, including concatenated frames', flush=True)

            valid = gzip.compress(b'bounded', mtime=0) if module == 'gzip' else reference.compress(b'bounded')
            bad_inputs = [b'', b'garbage', valid[:-1], valid[:len(valid)//2]]
            if module == 'gzip':
                bad_inputs += [valid[:-8] + bytes([valid[-8] ^ 1]) + valid[-7:]]
            else:
                checked_frame = native_frames[1][1]
                bad_inputs.append(checked_frame[:-1] + bytes([checked_frame[-1] ^ 1]))
                bad_inputs.append(bytes.fromhex('28b52ffd210100010000'))
            code = [f'use std::compression::{module};\nfn main()->i32{{\n']
            for malformed in bad_inputs:
                code.append('{\n' + declaration('input', malformed) + 'let mut output:[u8;64]=[0;64];')
                workspace = ''
                if module == 'zstd':
                    code.append('let mut workspace:[u8;131072]=[0;131072];'); workspace = ',&mut workspace[..]'
                code.append(f'match {module}::decompress(&input[..],&mut output[..]{workspace}){{Ok(v)=>{{drop(v);return 5;}},Err(e)=>{{drop(e);}}}}\n}}\n')
            code.append('{\n' + declaration('input', valid) + 'let mut output:[u8;2]=[0;2];')
            workspace = ''
            if module == 'zstd':
                code.append('let mut workspace:[u8;131072]=[0;131072];'); workspace = ',&mut workspace[..]'
            code.append(f'match {module}::decompress(&input[..],&mut output[..]{workspace}){{Ok(v)=>{{drop(v);return 6;}},Err(e)=>{{drop(e);}}}}\n}}\n')
            code.append('{let input:[u8;0]=[];let mut output:[u8;64]=[0;64];let mut workspace:[u64;1]=[0;1];')
            fields = 'level:1' + (',checksum:true' if module == 'zstd' else '')
            code.append(f'let params={module}::Params{{{fields}}};match {module}::compress(&input[..],&mut output[..],&params,&mut workspace[..]){{Ok(v)=>{{drop(v);return 7;}},Err(e)=>{{drop(e);}}}}\n}}\n0}}')
            assert execute(module + '_errors', ''.join(code)) == []
            print(f'{module}: truncation, malformed input and bounded-buffer/workspace errors', flush=True)


if __name__ == '__main__':
    main()
