#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Targeted streaming, dictionary and entropy interoperability for native compression."""
import argparse
import gzip
from pathlib import Path
import random
import shlex
import subprocess
from check_compression import declaration, Zstd
from compression_reference import DictReference

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corboc',type=Path,required=True)
    p.add_argument('--cc',default='cc');p.add_argument('--runner',default='')
    p.add_argument('--keep',type=Path,required=True)
    p.add_argument('--stdlib-dir',type=Path,default=ROOT/'stdlib/src')
    p.add_argument('--reuse-c',type=Path,help='Compile previously generated, identical fixture C for another target')
    p.add_argument('--only',choices=['stream','dictionary','entropy'],action='append')
    a=p.parse_args();root=a.keep.resolve();(root/'src').mkdir(parents=True,exist_ok=True)
    (root/'package.toml').write_text('[package]\nname="compression_extensions"\n')
    def execute(label,source):
        (root/'src/main.crb').write_text(source)
        c=root/(label+'.c');exe=root/(label+'.exe')
        if a.reuse_c:
            c.write_bytes((a.reuse_c/(label+'.c')).read_bytes())
        else:
            r=subprocess.run([a.corboc.resolve(),'--emit-package-c',root,'--stdlib-dir',a.stdlib_dir.resolve()],capture_output=True,timeout=240)
            assert r.returncode==0 and r.stdout.startswith(b'#'),(label,r.returncode,r.stdout[:200],r.stderr)
            c.write_bytes(r.stdout)
        subprocess.run([*shlex.split(a.cc),'-std=c11','-pthread','-O2','-fsanitize=undefined','-fno-sanitize-recover=all',c,'-lm','-o',exe],check=True,timeout=300)
        r=subprocess.run([*shlex.split(a.runner),exe],capture_output=True,timeout=120)
        assert r.returncode==0 and not r.stderr,(label,r.returncode,r.stdout[-500:],r.stderr)
        return [int(v) for v in r.stdout.splitlines()]
    ref=Zstd();dictref=DictReference()
    if not a.only or 'stream' in a.only:
        template=(ROOT/'validation/fixtures/compression/stream.crb.in').read_text()
        for codec in ['gzip','zstd']:
            source=template.replace('ENCDICT',',&empty[..]' if codec=='zstd' else '').replace('DECDICT',',&empty[..]' if codec=='zstd' else '').replace('CODEC',codec).replace('ENCARGS','3,true,' if codec=='zstd' else '6,').replace('DECARGS2',',&mut scratch2[..]' if codec=='zstd' else '').replace('DECARGS',',&mut scratch[..]' if codec=='zstd' else '')
            if codec=='zstd':source=source.replace('let empty:[u8;0]=[];', 'let empty:[u8;32]=[97;32];')
            values=execute(codec+'_stream',source);n=values[0];frame=bytes(values[1:n+1]);assert values[n+1:]==[100,1],values[-10:]
            decoded=gzip.decompress(frame) if codec=='gzip' else dictref.decompress(frame,b'a'*32,100)
            assert decoded==b'a'*100
            print(codec+': fragmented input/output, backpressure, EOF, reset, state errors and frame bounds passed',flush=True)
    if not a.only or 'dictionary' in a.only:
        trained=dictref.train();raw=b'method=GET status=200 payload=hello content-type=text/plain;'*8
        data=b'method=GET /users/42 status=200 content-type=text/plain; payload=hello resource id 3 with data of user 4'*3
        for label,dictionary in [('raw',raw),('trained',trained)]:
            frame=dictref.compress(data,dictionary)
            source='use std::compression::zstd;\nfn main()->i32{\n'+declaration('dictionary',dictionary)+declaration('data',data)+declaration('reference',frame)+'''
let mut output:[u8;4096]=[0;4096];let mut work:[u64;36864]=[0;36864];let mut scratch:[u8;131072]=[0;131072];let mut restored:[u8;1024]=[0;1024];let params=zstd::Params{level:3,checksum:true};
let n=match zstd::compress_with_dictionary(&data[..],&mut output[..],&params,&mut work[..],&dictionary[..]){Ok(v)=>{v},Err(e)=>{drop(e);return 1;}};print(n);let mut i:u64=0;while i<n as u64{print(output[i]);i=i+1;}
let n=match zstd::decompress_with_dictionary(&reference[..],&mut restored[..],&mut scratch[..],&dictionary[..]){Ok(v)=>{v as u64},Err(e)=>{drop(e);return 2;}};if n!=294{return 3;}i=0;while i<n{if restored[i]!=data[i]{return 4;}i=i+1;}0}
'''
            # Use the independently calculated length, not a codec's own reported count.
            source=source.replace('n!=294','n!='+str(len(data)))
            values=execute('dictionary_'+label,source);assert len(values)==values[0]+1
            assert dictref.decompress(bytes(values[1:]),dictionary,len(data))==data
            print('zstd: '+label+' dictionary interoperability in both directions passed',flush=True)
        errors=(ROOT/'validation/fixtures/compression/dictionary_errors.crb.in').read_text().replace('TRAINED',declaration('dictionary',trained)).replace('FRAME',declaration('frame',dictref.compress(data,trained)))
        assert execute('dictionary_errors',errors)==[1]
        print('zstd: missing, mismatched and malformed dictionaries rejected',flush=True)
    if not a.only or 'entropy' in a.only:
        rng=random.Random(1642);data=bytes(rng.choices(range(16),weights=[80]+[1]*15,k=4096))
        for codec in ['gzip','zstd']:
            fields='level:6'+(',checksum:true' if codec=='zstd' else '')
            source=f'use std::compression::{codec};\nfn main()->i32{{\n'+declaration('data',data)+f'let mut output:[u8;12288]=[0;12288];let mut work:[u64;36864]=[0;36864];let params={codec}::Params{{{fields}}};'+f'let n=match {codec}::compress(&data[..],&mut output[..],&params,&mut work[..]){{Ok(v)=>{{v}},Err(e)=>{{drop(e);return 1;}}}};print(n);let mut i:u64=0;while i<n as u64{{print(output[i]);i=i+1;}}0}}'
            roundtrip='let mut restored:[u8;4096]=[0;4096];let mut scratch:[u8;131072]=[0;131072];let count=match '+codec+'::decompress(&output[0..n],&mut restored[..]'+(',&mut scratch[..]' if codec=='zstd' else '')+'){Ok(v)=>{v},Err(e)=>{drop(e);return 2;}};if count!=4096{return 3;}i=0;while i<4096{if restored[i]!=data[i]{return 4;}i=i+1;}'
            if codec=='zstd':
                roundtrip+='let n=match zstd::compress(&data[0..511],&mut output[..],&params,&mut work[..]){Ok(v)=>{v},Err(e)=>{drop(e);return 5;}};let count=match zstd::decompress(&output[0..n],&mut restored[..],&mut scratch[..]){Ok(v)=>{v},Err(e)=>{drop(e);return 6;}};if count!=511{return 7;}i=0;while i<511{if restored[i]!=data[i]{return 8;}i=i+1;}'
            source=source[:-2]+roundtrip+'0}'
            values=execute(codec+'_entropy',source);frame=bytes(values[1:]);assert len(frame)==values[0]
            decoded=gzip.decompress(frame) if codec=='gzip' else ref.decompress(frame,len(data))
            assert decoded==data
            print(f'{codec}: weighted 4096-byte input -> {len(frame)} bytes, reference decoding passed',flush=True)


if __name__=='__main__':main()
