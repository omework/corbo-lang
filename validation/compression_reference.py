# SPDX-License-Identifier: MIT OR Apache-2.0
"""Test-only libzstd dictionary oracle; never linked into the standard library."""
import ctypes,ctypes.util
class DictReference:
 def __init__(self):
  self.lib=ctypes.CDLL(ctypes.util.find_library('zstd'));l=self.lib
  for name in ['ZSTD_createCCtx','ZSTD_createDCtx']:
   getattr(l,name).restype=ctypes.c_void_p
  for name in ['ZSTD_freeCCtx','ZSTD_freeDCtx']:
   getattr(l,name).argtypes=[ctypes.c_void_p]
  for name in ['ZSTD_compress_usingDict','ZSTD_decompress_usingDict']:
   f=getattr(l,name);f.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]+([ctypes.c_int] if 'compress_' in name and 'decompress' not in name else []);f.restype=ctypes.c_size_t
  l.ZSTD_isError.argtypes=[ctypes.c_size_t];l.ZSTD_isError.restype=ctypes.c_uint
  l.ZSTD_getErrorName.argtypes=[ctypes.c_size_t];l.ZSTD_getErrorName.restype=ctypes.c_char_p
  l.ZDICT_trainFromBuffer.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_uint];l.ZDICT_trainFromBuffer.restype=ctypes.c_size_t
 def check(self,n):
  assert not self.lib.ZSTD_isError(n),self.lib.ZSTD_getErrorName(n);return n
 def train(self):
  samples=[f'method=GET /users/{i} status=200 content-type=text/plain; payload=hello resource id {i%13} with data of user {i%19}'.encode() for i in range(512)]
  data=b''.join(samples);sizes=(ctypes.c_size_t*len(samples))(*map(len,samples));out=ctypes.create_string_buffer(1024);n=self.check(self.lib.ZDICT_trainFromBuffer(out,1024,data,sizes,len(samples)));return out.raw[:n]
 def compress(self,data,dictionary):
  c=self.lib.ZSTD_createCCtx();out=ctypes.create_string_buffer(len(data)*2+4096)
  try:n=self.check(self.lib.ZSTD_compress_usingDict(c,out,len(out),data,len(data),dictionary,len(dictionary),5));return out.raw[:n]
  finally:self.lib.ZSTD_freeCCtx(c)
 def decompress(self,data,dictionary,capacity):
  c=self.lib.ZSTD_createDCtx();out=ctypes.create_string_buffer(max(capacity,1))
  try:n=self.check(self.lib.ZSTD_decompress_usingDict(c,out,capacity,data,len(data),dictionary,len(dictionary)));return out.raw[:n]
  finally:self.lib.ZSTD_freeDCtx(c)
