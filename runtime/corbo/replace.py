#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
"""Differential backend adapter: replace exact reference sections, never user code."""
from pathlib import Path
import argparse,importlib.util
ROOT=Path(__file__).resolve().parents[1]
SECTIONS={
 'base_runtime':['memory/metrics_storage.h','memory/datastack.c.inc','collections/vector.c.inc','memory/region_release.c.inc','async/task_header.c.inc','async/mutex.c.inc','async/channel.c.inc'],
 'task_runtime':['async/scheduler.c.inc'],'pool_runtime':['memory/pools.c.inc','collections/vector_owned.c.inc'],
 'task_value_runtime':['async/values.c.inc'],'native_runtime':['async/threads.c.inc'],
 'reclaim_runtime':['memory/reclaim.c.inc'],'map_runtime':['collections/hashmap.c.inc'],
 'readiness_runtime':['async/readiness.c.inc'],'completion_runtime':['async/completion.c.inc'],
 'c_runtime_api':['runtime_api.c.inc'],
}
def replace(source,compiled):
    """Replace exact C-reference sections with compiled Corbo sections for differential tests; never rewrite application code."""
    threaded=(ROOT/'async/scheduler.c.inc').read_text() in source
    for name,paths in SECTIONS.items():
        old=''.join((ROOT/path).read_text()for path in paths)
        if name=='reclaim_runtime':
            lines=[];enabled=True
            for line in old.splitlines(keepends=True):
                if line=='#if CORBO_THREADED\n':enabled=threaded
                elif line=='#endif /* CORBO_THREADED */\n':enabled=True
                elif enabled:lines.append(line)
            old=''.join(lines)
        if old in source:
            assert source.count(old)==1,name
            source=source.replace(old,(compiled/(name+'.c.inc')).read_text())
    if threaded:source='#define CORBO_RT_THREADED 1\n'+source
    assert (ROOT/'memory/datastack.c.inc').read_text()not in source
    return source
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--compiled',type=Path,required=True);a=p.parse_args();a.output.write_text(replace(a.source.read_text(),a.compiled))
