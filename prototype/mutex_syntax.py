"""Nominal types used by the compiler's mutex and guard operations."""

MUTEX_TYPES = ('Mutex', 'AsyncMutex')
GUARD_TYPES = ('MutexGuard', 'AsyncMutexGuard')


def payload_type(typ, families=MUTEX_TYPES):
    if typ and typ.endswith('>'):
        family, _, payload = typ.partition('<')
        if family in families:
            return payload[:-1]
    return None
