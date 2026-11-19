"""Infer storage-kind obligations with the existing path-sensitive asset flow.

This supplements source equality/lifetime contracts; it never promotes storage.
Only root parameter obligations are materialized by current async variants.
"""
from owned_join_types import OWNED_JOIN_TYPES, owned_join_mode
from exchange_join_types import EXCHANGE_JOIN_TYPES, exchange_join_mode, exchange_payload_type
from constraints import ConstraintAnalyzer, Context, Value, UNKNOWN, join_values
from dataclasses import replace
from handle_types import public_storage
from handle_exchange_types import exchange_element


class StorageContext(Context):
    def completed_task(self, task):
        if not isinstance(task, Value) or task.mode not in ('task', 'execution'):
            return UNKNOWN
        mode, typ = self.analyzer.async_functions[task.typ].args[2]
        if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
            fields = dict(task.task_result_fields)
            payloads = tuple(fields.get(arm, task.task_result_assets) for arm in ('ok', 'err'))
            if task.mode == 'execution':
                mode = exchange_join_mode(typ if mode == 'buffered_handle_exchange' else EXCHANGE_JOIN_TYPES[mode])
                typ = exchange_payload_type(mode)
            return Value(mode, typ, task.task_result_assets, exchange_payloads=payloads)
        if task.mode == 'execution':
            if mode in ('owned', *OWNED_JOIN_TYPES):
                return Value(owned_join_mode(mode), typ,
                             task.task_result_assets, task.task_result_fields)
            return UNKNOWN
        if mode in ('owned', *OWNED_JOIN_TYPES):
            return Value(mode, typ, task.task_result_assets, task.task_result_fields)
        if mode in ('ref', 'mut'):
            return Value(mode, typ, task.task_reference_assets)
        return Value(mode, typ)

    def expression(self, expr, state, line, expected_array=None):
        if expr and expr[0] == 'array_copy' and expr[1][0] == 'name':
            value = self.lookup(expr[1][1], state, line)
            self.analyzer.copy_storage_hook(self, value, line)
        if expr and expr[0] == 'task_select':
            current, values = state, []
            for branch in expr[1]:
                paths, task = self.expression(branch, current, line)
                if 'next' not in paths:
                    return paths, UNKNOWN
                current = paths['next']
                values.append(self.completed_task(task))
            value = join_values(values)
            return {'next': current}, replace(value, mode='selection:' + value.mode)
        if expr and expr[0] == 'await':
            paths, task = self.expression(expr[1], state, line)
            if isinstance(task, Value) and task.mode.startswith('selection:'):
                return paths, replace(task, mode=task.mode.removeprefix('selection:'))
            if not isinstance(task, Value) or task.mode not in ('task', 'execution'):
                return paths, UNKNOWN
            if task.mode == 'execution':
                for current in paths.values():
                    for token in task.execution_tokens:
                        current.pending_executions.pop(token, None)
            return paths, self.completed_task(task)
        return super().expression(expr, state, line, expected_array)

    def nodes(self, nodes, state, valued=False, expected_array=None):
        nodes = [replace(node, op='print_expr') if node.op == 'await_statement' else node for node in nodes]
        return super().nodes(nodes, state, valued, expected_array)


def infer_storage_requirements(functions, async_functions, effects, results,
                               constraints, enums, error):
    catalog = dict(functions) | dict(async_functions)
    structures = set(enums)
    analyzer = ConstraintAnalyzer(functions, effects, results, error, enums, async_functions)
    analyzer.summaries.update(constraints)

    def require(context, value, required, line):
        if isinstance(value, Value) and value.mode in ('task', 'execution'):
            value = context.completed_task(value)
        if not isinstance(value, Value) or value.typ not in structures:
            return
        demands = dict(context.node.storage_requirements)
        def demand(index):
            previous = demands.get(index)
            if previous is not None and previous != required:
                context.fail(line, 'exigences de stockage incompatibles : local T et allocation A<T>')
            demands[index] = required
        for asset in value.assets:
            source = asset.source
            if source.kind == 'allocation_parameter' and context.params[source.index][1] == 'handle_option':
                declared = dict(context.node.join_storage_parameters).get(context.params[source.index][0], 'pool')
                if required != declared:
                    context.fail(line, 'exigence de stockage incompatible avec le type Option déclaré')
            elif source.kind == 'allocation_parameter' and context.params[source.index][2] in structures:
                demand(source.index)
            elif (source.kind == 'allocation_parameter'
                  and exchange_element(context.params[source.index][2]) == value.typ):
                declared = dict(context.node.join_storage_parameters).get(context.params[source.index][0], 'pool')
                if required != declared:
                    context.fail(line, 'exigence de stockage incompatible avec le résultat déclaré (T / A<T>)')
            elif source.kind == 'local':
                actual = 'local' if source.name == 'data stack implicite' else 'pool'
                if actual != required:
                    context.fail(line, f'exigence de stockage {required} incompatible avec la valeur {actual} '
                                 f'(T local / allocation A<T> ; distinction valeur {value.typ} / allocation A<{value.typ}>)')
            elif source.kind == 'allocation_field_parameter' and source.element in structures:
                # This metadata is emitted for owned A<T> fields, unlike
                # borrowed fields. Their storage is independent of the carrier.
                if required != 'pool':
                    context.fail(line, 'exigence de stockage local incompatible avec un champ allocation A<T>')
            elif source.kind in ('source_parameter', 'vector_element_parameter'):
                if required != 'pool':
                    context.fail(line, 'exigence de stockage local incompatible avec une allocation de pool')
            elif source.kind == 'task_result_parameter':
                definition = context.analyzer.async_functions[context.params[source.index][2]]
                actual = getattr(definition, 'join_storage_result', None)
                if actual is None and getattr(definition, 'handle_result', False):
                    actual = 'pool'
                effect = getattr(definition, 'field_effect_summary', None)
                if actual is None and effect and effect.complete:
                    candidates = effect.completion_result.candidates
                    for candidate in candidates:
                        known = None
                        if candidate.kind == 'fresh' and candidate.source.kind == 'local_value':
                            known = 'local'
                        elif candidate.kind == 'fresh' and candidate.source.kind == 'source_parameter':
                            known = 'pool'
                        elif candidate.kind == 'parameter' or (candidate.kind == 'fresh'
                                and candidate.source.kind == 'allocation_parameter'):
                            index = candidate.parameter if candidate.kind == 'parameter' else candidate.source.index
                            name = definition.args[1][index][0]
                            known = dict(getattr(definition, 'storage_requirements', ())).get(index)
                            if name in getattr(definition, 'handle_parameters', ()):
                                known = 'pool'
                        if known is not None and known != required:
                            context.fail(line, f'exigence de stockage {required} incompatible avec un résultat de tâche {known}')
                if actual is None:
                    # The opaque input's completion source is an obligation
                    # on its caller, just like an owned structure parameter.
                    demand(source.index)
                elif actual != required:
                    context.fail(line, f'exigence de stockage {required} incompatible avec le résultat de tâche {actual}')
                else:
                    demand(source.index)
            else:
                context.fail(line, 'prototype : exigence de stockage sur une projection non raccordée')
        context.node.storage_requirements = tuple(sorted(demands.items()))

    def annotation(context, value, typ, line):
        if (kind := public_storage(typ, structures)) is not None:
            require(context, value, kind, line)
        elif typ in structures:
            require(context, value, 'local', line)
        elif typ.startswith('A<') and typ[2:-1] in structures:
            require(context, value, 'pool', line)

    def copy_requirement(context, value, line):
        if not isinstance(value, Value) or value.typ not in structures:
            return
        if value.inline_path or any(choice.inline_path for choice in value.structure_choices):
            # Interior values have no pool of their own nominal type.
            require(context, value, 'local', line)
        indexes = {asset.source.index for asset in value.assets
                   if asset.source.kind == 'allocation_parameter'}
        context.node.copied_structure_parameters |= frozenset(indexes)

    def call(context, callee, actuals, line):
        for index, required in getattr(callee, 'storage_requirements', ()):
            require(context, actuals[index], required, line)
        for index in callee.copied_structure_parameters:
            copy_requirement(context, actuals[index], line)

    analyzer.copy_storage_hook = copy_requirement
    analyzer.storage_annotation_hook = annotation
    analyzer.storage_call_hook = call
    analyzer.storage_vector_item_hook = lambda context, value, line: require(context, value, 'local', line)
    for node in catalog.values():
        node.copied_structure_parameters = frozenset()
        joined = dict(getattr(node, 'join_storage_parameters', ()))
        node.storage_requirements = tuple((i, joined.get(name, 'pool'))
                                          for i, (name, _, typ) in enumerate(node.args[1])
                                          if typ in structures and (name in node.handle_parameters or name in joined))
        node.storage_requirements += tuple((i, kind) for i, (_, _, typ) in enumerate(node.args[1])
                                           if (kind := public_storage(typ, structures)) is not None)

    def relevant(value):
        if hasattr(value, 'op'):
            annotation = getattr(value, 'annotation', None)
            if annotation and public_storage(annotation, structures) or annotation in structures or (annotation and annotation.startswith('A<')
                                             and annotation[2:-1] in structures):
                return True
            return relevant(value.args)
        if isinstance(value, (tuple, list)):
            if value and value[0] == 'array_copy':
                return True
            if value and value[0] in ('array_vector_push', 'array_buffered_replace', 'array_buffered_try_push'):
                return True
            if len(value) == 3 and value[0] == 'call' and isinstance(value[1], str) and value[1] in catalog:
                if catalog[value[1]].storage_requirements or catalog[value[1]].copied_structure_parameters:
                    return True
            if len(value) == 4 and value[0] == 'method_call' and isinstance(value[2], str):
                if value[2] == 'push':
                    return True
                if any(name.endswith('.' + value[2]) and (node.storage_requirements or node.copied_structure_parameters)
                       for name, node in catalog.items()):
                    return True
            return any(relevant(item) for item in value)
        return False

    while True:
        previous = {name: (node.storage_requirements, node.copied_structure_parameters) for name, node in catalog.items()}
        for node in catalog.values():
            if (node.args[2][0] == 'owned' and node.args[2][1] in structures) or public_storage(node.args[2][1], structures) or relevant(node.args[3]):
                StorageContext(analyzer, node).infer()
        if all((node.storage_requirements, node.copied_structure_parameters) == previous[name] for name, node in catalog.items()):
            return
