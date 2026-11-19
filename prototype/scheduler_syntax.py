"""Static signature contract for a scheduler installed by main."""

SCHEDULER_PARAMETERS = {
    'spawn': ('owned', 'runtime::Future'),
    'spawn_blocking': ('owned', 'runtime::Future'),
    'wake': ('task_id', 'runtime::TaskId'),
}


def check_scheduler_methods(typ, methods, fail):
    for name, parameter in SCHEDULER_PARAMETERS.items():
        method = methods.get((typ, name))
        if method is None:
            fail(f"le scheduler {typ} doit fournir '{name}'")
        _, params, result, _ = method.args
        signature = tuple((mode, declared) for _, mode, declared in params)
        if signature != (('mut', typ), parameter) or result != ('void', 'Void'):
            fail(f"signature incompatible pour '{typ}.{name}'")
