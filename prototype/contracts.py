"""Body-free function interfaces consumed by the modular memory checker."""
from dataclasses import dataclass
from constraints import FunctionConstraints
from effects import FunctionEffects
from results import FunctionResult


@dataclass(frozen=True)
class FunctionContract:
    parameters: tuple[tuple[str, str, str], ...]
    result_type: tuple[str, str]
    effects: FunctionEffects
    result: FunctionResult
    constraints: FunctionConstraints
    mutable_parameters: frozenset[str] = frozenset()
    handle_parameters: frozenset[str] = frozenset()
    handle_result: bool = False
    static_async_parameters: frozenset[int] = frozenset()
    synchronous_task_slots: int = 0
    created_tasks: frozenset[str] = frozenset()
    abandoned_tasks: frozenset[str] = frozenset()
    storage_requirements: tuple[tuple[int, str], ...] = ()
    join_storage_result: str | None = None
    lock_contract: bool | None = None
    lock_parameters: frozenset[int] = frozenset()
    distinct_lock_parameters: frozenset[tuple[int, int]] = frozenset()
    returned_lock_parameters: frozenset[int] = frozenset()
    copied_lock_parameters: frozenset[int] = frozenset()
    live_lock_arguments: frozenset[tuple[int, int]] = frozenset()
    hashmap_writes: tuple[tuple[tuple[int, str | int, int | None], ...], ...] = ()
    branch_independent: bool = False
    branch_pools: frozenset[str] = frozenset()


def function_contracts(functions, effects, results, constraints):
    return {name: FunctionContract(tuple(node.args[1]), node.args[2], effects[name],
                                   results[name], constraints[name], node.mutable_parameters,
                                   node.handle_parameters, node.handle_result,
                                   storage_requirements=getattr(node, 'storage_requirements', ()),
                                   join_storage_result=node.join_storage_result,
                                   lock_contract=node.lock_contract,
                                   lock_parameters=frozenset({0}) if node.lock_contract is not None else frozenset(),
                                   returned_lock_parameters=frozenset({0}) if node.lock_contract else frozenset(),
                                   hashmap_writes=node.hashmap_writes, branch_independent=node.branch_independent,
                                   branch_pools=node.branch_pools)
            for name, node in functions.items()}
