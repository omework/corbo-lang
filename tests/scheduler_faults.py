"""Reject logical task submissions without depending on worker creation counts."""


def inject_submission_failure(code, *, asynchronous=True, at=None, maximum=None):
    """at=None rejects all; at=0 rejects none; maximum asserts a launch count."""
    name = 'task_async_start_mode' if asynchronous else 'task_thread_start_mode'
    declaration = ('static void ' if asynchronous else 'static int ') + name + '('
    start = code.index(declaration)
    end = code.index('\nstatic ', start + len(declaration))
    before, body, after = code[:start], code[start:end], code[end:]
    anchor = 'int error = task_default_submit(task);'
    assert body.count(anchor) == 1
    counter = 'injected_async_submissions' if asynchronous else 'injected_sync_submissions'
    prefix = ''
    if at is None:
        condition = '1'
    elif at == 0 and maximum is None:
        return code
    else:
        prefix = f'static _Atomic int {counter};\n'
        condition = f'atomic_fetch_add(&{counter}, 1) + 1 == {at}'
    replacement = f'int error = ({condition}) ? EAGAIN : task_default_submit(task);'
    if maximum is not None:
        replacement += f'\n        if (atomic_load(&{counter}) > {maximum}) abort();'
    return before + prefix + body.replace(anchor, replacement) + after
