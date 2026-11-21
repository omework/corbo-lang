# SPDX-License-Identifier: MIT OR Apache-2.0
"""C ABI signatures only. Implementations are the corresponding Corbo functions."""
AGGREGATES={'Owned','ClassicStack','TaskValue','TaskCompletion','CorboStackMark','CorboStackInfo','CorboMemoryStats'}
EXPORTS=[]
def add(group,name,result,*parameters):
    """Register one typed C ABI export; its implementation remains in the corresponding Corbo source function."""
    EXPORTS.append((group,name,result,parameters))
for name,result,params in [
 ('mutex_create','uintptr_t',[('bool','asynchronous')]),('mutex_acquire','void',[('uintptr_t','raw')]),
 ('mutex_release','void',[('uintptr_t','raw')]),('mutex_destroy','void',[('uintptr_t','raw')]),
 ('mutex_poll','bool',[('Task*','child'),('uintptr_t','raw')]),('mutex_detach','void',[('Task*','child')])]:add('base_runtime',name,result,*params)
for name,result,params in [
 ('memory_cursor','void',[('size_t','next')]),
 ('reserve','void',[('uint64_t','bytes')]),('push','void*',[('size_t','size'),('size_t','alignment'),('size_t','count')]),('release','void',[]),('take','size_t',[('int*','used'),('size_t','count')]),('numeric','long long',[('int','op'),('long long','left'),('long long','right')]),
 ('region_error','void',[]),('region_default_capacity','size_t',[]),('region_metadata','RegionBand*',[]),('region_reserve','void',[('RegionBand*','band'),('size_t','bytes'),('size_t','maximum')]),('region_release_band','void',[('RegionBand*','band')]),('region_stride','size_t',[('size_t','bytes')]),('region_enter','void',[('size_t','bytes'),('size_t','count'),('size_t','inferred')]),('region_restore','void',[('RegionBand*','mark')]),('region_new','void',[('Region*','region'),('size_t','width'),('int','owned'),('int','dedicated')]),('region_drop','void',[('Region*','region')]),('region_add','unsigned char*',[('Region*','region')]),('region_release','void',[]),
 ('value_region_new','void',[('Region*','region'),('size_t','width'),('int','owned'),('int','dedicated')]),('value_region_add','unsigned char*',[('Region*','region')]),('value_region_drop','void',[('Region*','region')]),('scoped_region_enter','void',[('size_t','bytes'),('size_t','count'),('size_t','inferred')]),('scoped_region_restore','void',[('RegionBand*','mark')]),
 ('region_push_owned','void',[('Region*','region'),('Region*','item'),('int*','slot')]),('region_push','void',[('Region*','region'),('long long','value')]),('region_push_row','void',[('Region*','region'),('const long long*','row')]),('region_read_row','long long',[('Region*','region'),('size_t','index'),('size_t','field')]),('region_append','void',[('Region*','region'),('const unsigned char*','data'),('size_t','count')]),('region_read','long long',[('Region*','region'),('size_t','index')]),
]:add('base_runtime',name,result,*params)
for name,result,params in [
 ('destroy_region','void',[('void*','pointer')]),('storage_error','void',[]),('new_pool','Pools*',[('size_t','slots'),('size_t','bytes'),('size_t','arms')]),('pool_take','Owned',[('Pools*','pool'),('size_t','arm')]),('pool_try_take','bool',[('Owned*','out'),('Pools*','pool'),('size_t','arm')]),('put','void',[('Owned*','value')]),('dispose_owned','void',[('void*','pointer')]),('value_region_append','void',[('Region*','region'),('const unsigned char*','data'),('size_t','count')]),('vector_remove','void',[('Region*','region'),('uint64_t','index'),('void*','out')]),('vector_pop','bool',[('Region*','region'),('void*','out')]),('destroy_owned_region','void',[('void*','region')])]:add('pool_runtime',name,result,*params)
for name,result,params in [('map_align','size_t',[('size_t','bytes')]),('map_new','RegionalMap*',[('size_t','width'),('void (*{name})(void*)','dispose')]),('map_extend','void',[('RegionalMap*','map'),('size_t','bytes')]),('map_link','size_t*',[('RegionalMap*','map'),('uint64_t','key')]),('map_get','void*',[('RegionalMap*','map'),('uint64_t','key')]),('map_insert','bool',[('RegionalMap*','map'),('uint64_t','key'),('const void*','incoming'),('void*','previous')]),('map_remove','bool',[('RegionalMap*','map'),('uint64_t','key'),('void*','previous')]),('map_drop','void',[('RegionalMap**','slot')])]:add('map_runtime',name,result,*params)
for name,result,params in [('release_pages','bool',[('unsigned char*','start'),('size_t','size')]),('reclaim_after','void',[('unsigned char*','start'),('size_t','live'),('size_t*','done'),('size_t','threshold'),('bool','force')]),('reclaim_band','void',[('RegionBand*','band'),('bool','force')]),('reclaim_scope','void',[('bool','force')])]:add('reclaim_runtime',name,result,*params)
POLL='bool (*{name})(Task*,bool)';DROP='void (*{name})(Task*)';DISPOSE='void (*{name})(TaskState*,bool)'
for name,result,params in [('task_enqueue','void',[('Task*','task')]),('task_publish','void',[('Task*','task')]),('task_await','bool',[('Task*','child'),('Task*','current')]),('task_poll_worker','void*',[('void*','unused')]),('task_spawn_with','void',[('Task*','task'),(POLL,'poll'),(DROP,'discard')]),('task_spawn','void',[('Task*','task'),(POLL,'poll')]),('task_join','void',[('Task*','task')]),('task_end','void',[])]:add('task_runtime',name,result,*params)
for name,result,params in [('swap_classic','ClassicStack',[('ClassicStack','next')]),('make_task_in','TaskValue',[('Region*','region'),('size_t','size'),(POLL,'poll'),('bool','dedicated')]),('task_metadata','void*',[('size_t','bytes')]),('task_unmap','void',[('void*','pointer'),('size_t','bytes')]),('make_task','TaskValue',[('size_t','size'),(POLL,'poll')]),('release_future','void',[('TaskState*','state'),('bool','completed'),('bool','taken')]),('task_abandoned','void',[('Task*','task')]),('start_task','TaskValue',[('TaskValue','value')]),('discard_handle','void',[('TaskValue','value')]),('join_task','TaskCompletion',[('TaskValue','value')]),('join_task_into','bool',[('TaskValue','value'),('void*','out'),('size_t','bytes')]),('discard_future','void',[('TaskValue','value')])]:add('task_value_runtime',name,result,*params)
for name,result,params in [('native_box','NativeBox*',[]),('native_release','void',[('NativeBox*','box')]),('worker_regions','void',[]),('native_run','void*',[('void*','box')]),('make_native','TaskValue',[('size_t','size'),(POLL,'run'),(DISPOSE,'dispose')]),('start_native','void',[('TaskValue','value')]),('release_native','void',[('TaskValue','value'),('bool','taken')]),('abandon_native','void',[('TaskValue','value')]),('dispose_handle_value','void',[('void*','value')]),('destroy_task_region','void',[('void*','region')]),('run_blocking','void*',[('void*','task')]),('start_blocking','TaskValue',[('TaskValue','value')]),('native_drain','void',[])]:add('native_runtime',name,result,*params)
for name,result,params in [('socket_interest','unsigned',[('uintptr_t','token')]),('socket_signal','void',[('uintptr_t','token'),('unsigned','mask'),('int64_t','status')]),('socket_dispatch','void',[('uintptr_t','event')]),('socket_events','void*',[('void*','unused')]),('socket_initialize','void',[]),('corbo_socket_wait','bool',[('Task*','child'),('uint64_t','descriptor'),('bool','write'),('int64_t*','out')])]:add('readiness_runtime',name,result,*params)
for name,result,params in [('completion_events','void*',[('void*','unused')]),('completion_initialize','void',[]),('corbo_socket_attach','int64_t',[('uint64_t','descriptor')]),('corbo_socket_complete','bool',[('Task*','child'),('uint64_t','descriptor'),('uintptr_t','address'),('int64_t*','out')])]:add('completion_runtime',name,result,*params)
for name,result,params in [
 ('corbo_memory_stats','CorboMemoryStats',[]),
 ('corbo_runtime_abi_version','unsigned',[]),('corbo_runtime_init','void',[('size_t','fixed'),('size_t','regions'),('size_t','region')]),('corbo_runtime_shutdown','void',[]),('corbo_datastack_alloc','void*',[('size_t','size'),('size_t','alignment'),('size_t','count')]),('corbo_datastack_mark','CorboStackMark',[]),('corbo_datastack_info','CorboStackInfo',[]),('corbo_datastack_rewind','void',[('CorboStackMark','mark')]),('corbo_free_pages','void',[]),('corbo_pool_create','CorboPool*',[('size_t','slots'),('size_t','size'),('size_t','arms')]),('corbo_pool_take','CorboAllocation',[('CorboPool*','pool'),('size_t','arm')]),('corbo_allocation_data','void*',[('const CorboAllocation*','allocation')]),('corbo_allocation_drop','void',[('CorboAllocation*','allocation')]),('corbo_region_enter','void',[('size_t','maximum'),('size_t','count')]),('corbo_region_new','void',[('CorboRegion*','region'),('size_t','size'),('bool','dedicated')]),('corbo_region_push','void*',[('CorboRegion*','region')]),('corbo_region_drop','void',[('CorboRegion*','region')]),('corbo_map_new','CorboHashMap*',[('size_t','size'),('void (*{name})(void*)','dispose')]),('corbo_map_get','void*',[('CorboHashMap*','map'),('uint64_t','key')]),('corbo_map_insert','bool',[('CorboHashMap*','map'),('uint64_t','key'),('const void*','incoming'),('void*','previous')]),('corbo_map_remove','bool',[('CorboHashMap*','map'),('uint64_t','key'),('void*','previous')]),('corbo_map_drop','void',[('CorboHashMap**','map')])]:add('c_runtime_api',name,result,*params)
AGGREGATES.add('CorboAllocation')
INPLACE_RETURNS={'start_task','start_blocking'}

def declaration(name,result,parameters):
    """Render a typed ABI signature, retaining exact callback types and public memory API linkage."""
    public=name.startswith('corbo_') and name not in {'corbo_socket_wait','corbo_socket_attach','corbo_socket_complete'}
    prefix='' if public else 'static __attribute__((unused)) '
    args=','.join(t.format(name=n) if '{name}' in t else t+' '+n for t,n in parameters)or'void'
    return prefix+result+' '+name+'('+args+')'

def wrapper(name,result,parameters):
    """Marshal scalar/aggregate arguments into the Corbo ABI and move aggregate results back without implementing runtime policy."""
    args=[]
    if result in AGGREGATES and name not in INPLACE_RETURNS:args.append('(uintptr_t)&out')
    for t,n in parameters:
        if t in AGGREGATES:args.append('(uintptr_t)&'+n)
        elif '*' in t:args.append('(uintptr_t)'+n)
        else:args.append(n)
    call='crb_'+name+'('+','.join(args)+')'
    if name in INPLACE_RETURNS:body=call+';return value;'
    elif result in AGGREGATES:body=result+' out;'+call+';return out;'
    elif result=='void':body=call+';'
    else:body='return ('+result+')'+call+';'
    return declaration(name,result,parameters)+'{'+body+'}\n'
