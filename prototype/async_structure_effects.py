"""Infer deferred reference-field writes, separately from execution/loan checking.

Completion and suspension summaries are distinct; neither runs at task creation.
They are not yet
an authorization to lower a field-changing call: the backend must also carry
the effects through handles and enforce the corresponding lifetimes.
"""

from owned_join_types import (
    OWNED_JOIN_TYPES, owned_join_mode,
)
from option_join_types import (
    OPTION_JOIN_TYPES, option_join_mode,
)
from exchange_join_types import (
    EXCHANGE_JOIN_TYPES, exchange_join_mode, exchange_payload_type,
)
from dataclasses import dataclass, replace
from collections import ChainMap
from types import SimpleNamespace
from handle_types import initial_handle_waits

from mutex_syntax import GUARD_TYPES, payload_type as mutex_payload
from numeric_core import EXTRA_MODES, NUMERIC_JOIN_FIELDS
from results import (
    BorrowTarget, FunctionResult, ResultAnalyzer, ResultContext, Value, VOID,
    borrowed_targets, merge_deferred_definite_fields, merge_deferred_map_paths, merge_task_owned_updates,
)
from array_syntax import INLINE_VECTOR_ELEMENTS, REFERENCE_VECTORS, reference_array_shape, merge_owned_values
from utf8_syntax import UTF8_BORROW_MODES, VALUE_MODES, PLAIN_RETURN_JOINS, PLAIN_JOIN_TYPES


FIELD_RESULT_MODES = ChainMap(OWNED_JOIN_TYPES, OPTION_JOIN_TYPES, EXCHANGE_JOIN_TYPES, dict.fromkeys(('scalar', 'bool', 'byte', 'char', 'void', 'ref', 'mut', 'async_execution', *EXTRA_MODES,
                                           'owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange', 'array')), VALUE_MODES)

MAP_STATE = '\0collection_completion'


def completion_hashmap_writes(node, summary=None):
    if summary is None:
        summary = node.field_effect_summary
    deferred = summary.completion_map_paths if summary is not None else ()
    direct = node.hashmap_writes
    if not any(direct) or not any(deferred):
        return direct if any(direct) else deferred
    # The direct summary and the awaited-handle summary project different
    # operations. Either projection can contain the last write to an entry.
    return tuple(dict.fromkeys(combined for left in direct for right in deferred
                               for combined in (left + right, right + left)))


class IncompleteStructureEffects(Exception):
    """An unsupported analysis must never masquerade as an empty effect."""


class ContractResultAnalyzer(ResultAnalyzer):
    """Demand synchronous summaries through their inference provider."""
    resolver = None

    def infer(self, name):
        if name in self.summaries or self.resolver is None:
            return super().infer(name)
        summary = self.resolver(name)
        if summary is None:
            raise IncompleteStructureEffects('contrat synchrone encore en cours d’inférence')
        self.summaries[name] = summary
        return summary


@dataclass(frozen=True)
class AsyncStructureEffects:
    parameters: tuple
    # None means unknown; () means a completed analysis found no field writes.
    structure_fields: tuple | None
    reason: str = ''
    may_complete: bool | None = None
    completion_result: FunctionResult | None = None
    suspension_result: FunctionResult | None = None
    may_suspend: bool | None = None
    suspension_reason: str = ''
    guarded_fields: tuple = ()
    guarded_writes: tuple = ()
    handle_wait_order: tuple[int, ...] = ()
    returned_handle_fields: tuple | None = None
    returned_handle_definite_fields: frozenset = frozenset()
    returned_handle_guarded_fields: tuple = ()
    returned_handle_guarded_writes: tuple = ()
    returned_handle_owned_writes: tuple = ()
    returned_handle_vector_updates: tuple = ()
    returned_handle_map_paths: tuple = ()
    completion_map_paths: tuple = ()

    @property
    def complete(self):
        """Normal-completion inference only; suspension coverage is separate."""
        return self.structure_fields is not None

    @property
    def suspension_complete(self):
        return self.suspension_result is not None


class AsyncStructureEffectAnalyzer:
    def __init__(self, definitions, sync_contracts, enums, error, *, sync_resolver=None):
        self.definitions = definitions
        self.error = error
        self.summaries = {}
        self.visiting = set()
        # Keep the admissible layouts shared with lowering: direct borrowed
        # fields and separately owned descendants have distinct obligations.
        from structure_shapes import async_structure_shapes
        self.owned_structures, self.reference_structures = async_structure_shapes(
            {typ: tuple(field for fields in variants.values() for field in fields)
             for typ, variants in enums.items()})
        # Only the published synchronous contracts cross this boundary. The
        # function bodies are deliberately absent from the symbolic adapter.
        functions = {name: SimpleNamespace(
            args=(name, contract.parameters, contract.result_type, ()), line=0)
            for name, contract in sync_contracts.items()}
        self.results = ContractResultAnalyzer(functions,
            {name: contract.effects for name, contract in sync_contracts.items()},
            error, enums, definitions)
        self.results.summaries = {name: contract.result for name, contract in sync_contracts.items()
                                 if contract.result is not None}
        self.results.resolver = sync_resolver
        self.results.async_summary_resolver = self.infer

    def infer_all(self):
        for name in self.definitions:
            self.infer(name)
        return self.summaries

    def infer(self, name):
        if name in self.summaries:
            return self.summaries[name]
        node = self.definitions[name]
        parameters = tuple(node.args[1])
        for _, mode, typ in parameters:
            layout = self.results.enums.get(typ, {}).get('')
            owned_graph = mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option') and typ in self.owned_structures
            if layout is not None and not owned_graph and (
                    mode not in ('ref', 'mut') or typ not in self.reference_structures):
                summary = AsyncStructureEffects(parameters, None,
                    'effets de champs des agrégats généraux non raccordés')
                self.summaries[name] = summary
                return summary
        if name in self.visiting:
            return AsyncStructureEffects(parameters, None, 'effets de champs async récursifs non résolus')
        self.visiting.add(name)
        try:
            context = StructureEffectContext(self, node)
            result = context.infer()
            guarded = tuple((index, fields) for index, fields in result.structure_fields
                            if index in context.mutex_parameters)
            result = replace(result, structure_fields=tuple((index, fields)
                for index, fields in result.structure_fields if index not in context.mutex_parameters))
            summary = AsyncStructureEffects(parameters, result.structure_fields,
                                            may_complete=context.has_completion,
                                            completion_result=result,
                                            suspension_result=context.suspension_summary(),
                                            may_suspend=context.has_suspension if not context.suspension_reason else None,
                                            suspension_reason=context.suspension_reason,
                                            guarded_fields=guarded,
                                            guarded_writes=tuple(sorted(context.guarded_writes)),
                                            handle_wait_order=initial_handle_waits(node),
                                            completion_map_paths=tuple(sorted(context.completion_map_paths, key=repr))
                                                if any(context.completion_map_paths) else (),
                                            returned_handle_fields=(tuple(
                                                (index, tuple(sorted(fields.items())))
                                                for index, fields in sorted(context.returned_handle_fields.items()))
                                                if context.returned_handle_fields is not None else None),
                                            returned_handle_definite_fields=frozenset(
                                                context.returned_handle_definite_fields or ()),
                                            returned_handle_guarded_fields=tuple(
                                                (index, tuple(sorted(fields.items())))
                                                for index, fields in sorted(context.returned_handle_guarded_fields.items()))
                                                if context.returned_handle_fields is not None else (),
                                            returned_handle_guarded_writes=tuple(sorted(context.returned_handle_guarded_writes))
                                                if context.returned_handle_fields is not None else (),
                                            returned_handle_owned_writes=tuple(
                                                (index, path, child) for (index, path), child
                                                in sorted(context.returned_handle_owned_writes.items()))
                                                if context.returned_handle_fields is not None else (),
                                            returned_handle_vector_updates=tuple(
                                                sorted(context.returned_handle_vector_updates.items()))
                                                if context.returned_handle_fields is not None else (),
                                            returned_handle_map_paths=tuple(sorted(context.returned_handle_map_paths, key=repr))
                                                if context.returned_handle_fields is not None
                                                and any(context.returned_handle_map_paths) else ())
        except (IncompleteStructureEffects, self.error) as error:
            summary = AsyncStructureEffects(parameters, None, str(error))
        finally:
            self.visiting.remove(name)
        self.summaries[name] = summary
        return summary

    def completion_symbol(self, name, summary):
        """Use the ordinary result-contract interpreter without a callee body."""
        return self.result_symbol(name, summary.parameters, summary.completion_result, 'completion')

    def result_symbol(self, name, parameters, result, phase):
        symbol = '\0async_' + phase + ':' + name
        self.results.functions[symbol] = SimpleNamespace(
            args=(symbol, parameters, (result.mode, result.typ), ()), line=0)
        self.results.effects[symbol] = SimpleNamespace(may_return=True)
        self.results.summaries[symbol] = result
        return symbol


class StructureEffectContext(ResultContext):
    def __init__(self, effects, node):
        # Result checking belongs to the existing checker. This pass collects
        # the states of injected structures at each continuing/returning exit.
        declared = node.args[2] if node.args[2][0] in (
            'ref', 'mut', 'owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange', *UTF8_BORROW_MODES) else ('void', 'Void')
        self.mutex_parameters = {index: payload
            for index, (_, mode, typ) in enumerate(node.args[1])
            if mode == 'ref' and (payload := mutex_payload(typ)) in effects.reference_structures}
        # Infer against a symbolic mutable payload. Only lock/reborrow grants
        # access to it in the backend. Keep the public signature unchanged.
        parameters = tuple((name, 'mut', self.mutex_parameters[index])
            if index in self.mutex_parameters else (name, mode, typ)
            for index, (name, mode, typ) in enumerate(node.args[1]))
        self.guarded_writes = set()
        super().__init__(effects.results, replace(node, args=(
            node.args[0], parameters, declared, node.args[3])))
        self.effects = effects
        self.pending = {}
        self.pending_map_keys = {}
        self.returned_handle_fields = {} if node.args[2][0] == 'async_execution' else None
        self.returned_handle_definite_fields = None
        self.returned_handle_guarded_fields = {}
        self.returned_handle_guarded_writes = set()
        self.returned_handle_owned_writes = {}
        self.returned_handle_vector_updates = {}
        self.returned_handle_map_paths = {}
        self.completion_map_paths = set()
        self.selections = {}
        self.has_completion = False
        self.has_suspension = False
        self.suspended_structures = {}
        self.suspended_owned_states = []
        self.suspended_vector_states = []
        self.suspension_reason = ''
        if any(mode in ('array_ref', 'array_mut') and reference_array_shape(typ)
               or mode == 'mut' and (typ.startswith('A<') or typ in REFERENCE_VECTORS
                   or typ in effects.results.enums and typ not in effects.reference_structures
                   and typ not in effects.owned_structures)
               for _, mode, typ in self.params):
            # Do not publish a FunctionResult with empty array/handle updates
            # when only injected structure fields have been observed.
            self.suspension_reason = 'effets suspendus des autres porteurs de références non raccordés'

    def update_structure(self, environment, name, carrier, changes, line):
        for index in self.mutex_parameters:
            if carrier.storage_owner != f'\0structure:{index}':
                continue
            for field, targets in changes.items():
                if '/' in field or any(target.kind != 'parameter' or self.params[target.parameter][1] != 'ref'
                                       for target in targets):
                    raise IncompleteStructureEffects('remplacement sous garde : emprunt partagé injecté requis')
                self.guarded_writes.update((index, field, target.parameter) for target in targets)
        super().update_structure(environment, name, carrier, changes, line)

    def observe_suspension(self, environment, line):
        self.has_suspension = True
        self.suspended_vector_states.append((line, environment.copy()))
        self.suspended_owned_states.append((line, {index: environment[f'\0structure:{index}']
                                                   for index in self.structure_inputs}))
        for index, original in self.structure_inputs.items():
            if self.params[index][1] == 'owned':
                # A moved carrier is internal to this state. Its current fields
                # are not stores into an external borrowed carrier on suspension.
                continue
            final = environment[f'\0structure:{index}']
            fields = self.suspended_structures.setdefault(index, {})
            for field, targets in final.fields:
                if any(target.kind not in ('field_parameter', 'parameter', 'detached_field_parameter')
                       or self.params[target.parameter][1] == 'owned' for target in targets):
                    # A temporary write restored before completion may still
                    # escape if a Select loser is destroyed at this suspension.
                    self.suspension_reason = 'cible non durable dans un champ au point de suspension'
                fields[field] = fields.get(field, frozenset()) | targets

    def suspension_summary(self):
        if self.suspension_reason:
            return None
        fields = tuple((index, tuple((field, targets) for field, targets in sorted(changes.items())
                       if targets != dict(self.structure_inputs[index].fields)[field]))
                       for index, changes in sorted(self.suspended_structures.items())
                       if index not in self.mutex_parameters and changes != dict(self.structure_inputs[index].fields))
        # Use the same owned-field contract representation as completion, but
        # collect only snapshots at outward suspension points.
        exits, writes = self.owned_exit_states, self.owned_field_writes
        self.owned_exit_states, self.owned_field_writes = self.suspended_owned_states, {}
        try:
            self.collect_owned_writes()
            owned = tuple((index, path, child) for (index, path), child in sorted(self.owned_field_writes.items())
                          if any(candidate.kind != 'owned_field_input' for candidate in child.candidates))
        except self.analyzer.error as error:
            self.suspension_reason = str(error)
            return None
        finally:
            self.owned_exit_states, self.owned_field_writes = exits, writes
        completion_paths = self.vector_write_paths
        self.vector_write_paths = {}
        try:
            for line, environment in self.suspended_vector_states:
                self.collect_vector_writes(environment, line)
            vectors = self.vector_write_summary()
        except self.analyzer.error as error:
            self.suspension_reason = str(error)
            return None
        finally:
            self.vector_write_paths = completion_paths
        return FunctionResult('void', 'Void', structure_fields=fields, owned_field_writes=owned,
                              vector_writes=vectors)

    def apply_async_result(self, name, parameters, result, actuals, environment, line, phase):
        branch = environment.copy()
        names = tuple(f'\0async_argument:{i}' for i in range(len(actuals)))
        for variable, value in zip(names, actuals):
            branch[variable] = value
        symbol = self.effects.result_symbol(name, parameters, result, phase)
        _, completed = super().expression(
            ('call', symbol, tuple(('name', variable) for variable in names)), branch, line)
        if phase == 'completion':
            paths = self.effects.summaries[name].completion_map_paths
            self.record_completed_map_paths(branch, self.map_return_paths(paths, actuals))
        if phase == 'completion' and self.effects.definitions[name].args[2][0] == 'async_execution':
            typ = self.effects.definitions[name].args[2][1]
            summary = self.effects.summaries[name]
            fields = (*(summary.returned_handle_fields or ()), *summary.returned_handle_guarded_fields)
            writes = self.guarded_write_sources(summary.returned_handle_guarded_writes)
            completed = Value('async_execution', typ,
                              deferred_field_updates=self.instantiate_deferred_fields(fields, actuals),
                              deferred_guarded_writes=self.instantiate_deferred_fields(writes, actuals),
                              deferred_owned_updates=self.instantiate_deferred_owned(
                                  summary.returned_handle_owned_writes, actuals, environment),
                              deferred_vector_updates=self.instantiate_deferred_vectors(
                                  summary.returned_handle_vector_updates, actuals),
                              deferred_map_paths=frozenset(self.map_return_paths(
                                  summary.returned_handle_map_paths, actuals)),
                              deferred_definite_fields=frozenset(
                                  (actuals[index], field) for index, field in summary.returned_handle_definite_fields))
        # Saved capture names must publish their writes to all carrier aliases.
        for index, _ in result.structure_fields:
            owner = branch[names[index]].storage_owner
            current = branch.get(owner)
            if isinstance(current, Value):
                for variable, alias in tuple(branch.items()):
                    if isinstance(alias, Value) and alias.storage_owner == owner:
                        branch[variable] = replace(alias, fields=current.fields)
        for index, *_ in result.vector_writes:
            current = branch[names[index]]
            if not isinstance(current, Value):
                continue
            for variable, alias in tuple(branch.items()):
                if isinstance(alias, Value) and alias.typ == current.typ and alias.structure_origins == current.structure_origins:
                    branch[variable] = replace(alias, handle_items=current.handle_items,
                        input_item_history=current.input_item_history,
                        input_items_written=current.input_items_written,
                        input_items_changed=current.input_items_changed)
        for variable in names:
            branch.pop(variable)
        return branch, completed

    def observe_child_suspensions(self, name, summary, actuals, environment, line):
        if summary.suspension_result is None:
            self.suspension_reason = summary.suspension_reason or summary.reason or 'effets suspendus inconnus'
            return
        if not summary.may_suspend:
            return
        blocks = self.blocks
        self.blocks = [(outer.copy(), shadows.copy()) for outer, shadows in blocks]
        try:
            branch, _ = self.apply_async_result(name, summary.parameters, summary.suspension_result,
                                               actuals, environment, line, 'suspension')
            self.observe_suspension(branch, line)
        except (IncompleteStructureEffects, self.effects.error) as error:
            self.suspension_reason = str(error)
        finally:
            self.blocks = blocks

    def observe_factory_suspensions(self, task, environment, line):
        if (task.deferred_suspension_updates is None or task.task_may_suspend is None
                or task.deferred_suspension_owned is None or task.deferred_suspension_vectors is None):
            self.suspension_reason = 'effets suspendus de fabrique synchrone non raccordés'
            return
        if not task.task_may_suspend:
            return
        branch = environment.copy()
        blocks = self.blocks
        self.blocks = [(outer.copy(), shadows.copy()) for outer, shadows in blocks]
        try:
            self.apply_deferred_owned(task.deferred_suspension_owned, branch)
            self.apply_deferred_vectors(task.deferred_suspension_vectors, branch)
            self.apply_factory_fields(task.deferred_suspension_updates, branch, line)
            self.observe_suspension(branch, line)
        except (IncompleteStructureEffects, self.effects.error) as error:
            self.suspension_reason = str(error)
        finally:
            self.blocks = blocks

    def apply_factory_fields(self, updates, environment, line):
        for carrier, fields in updates:
            temporary = '\0factory_carrier'
            environment[temporary] = carrier
            self.update_structure(environment, temporary, carrier, dict(fields), line)
            environment.pop(temporary)

    def complete_factory(self, task, environment, line):
        temporary = '\0factory_task'
        environment[temporary] = replace(task, mode='execution')
        try:
            mode, typ = self.effects.definitions[task.typ].args[2]
            if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
                part = {'next'}
                completed = self.async_owned_result_value(mode, typ, task.task_result_sources, task.task_result_fields)
            else:
                part, completed = super().expression(('task_join', temporary), environment, line)
        finally:
            environment.pop(temporary)
        if not isinstance(completed, Value) or completed.mode == 'unknown':
            raise IncompleteStructureEffects('résultat de fabrique synchrone non raccordé')
        # An inactive task's direct await cannot produce LaunchFailed.
        self.apply_deferred_owned(task.deferred_owned_updates, environment)
        self.apply_factory_fields(task.deferred_field_updates, environment, line)
        mode, typ = self.effects.definitions[task.typ].args[2]
        return part, replace(completed, mode=mode, typ=typ)

    def collect(self, value, line, environment=None):
        self.has_completion = True
        if environment is not None and MAP_STATE in environment:
            self.completion_map_paths.update(environment[MAP_STATE].deferred_map_paths)
        if self.returned_handle_fields is not None:
            self.collect_returned_handle_fields(value, line, environment)
        super().collect(VOID if self.declared[0] == 'void' else value, line, environment)

    def collect_returned_handle_fields(self, value, line, environment):
        if not isinstance(value, Value) or value.mode not in ('execution', 'async_execution'):
            self.returned_handle_fields = None
            return
        if not self.record_returned_guarded_writes(value.deferred_guarded_writes):
            self.returned_handle_fields = None
            return
        self.collect_deferred_owned(value.deferred_owned_updates, self.returned_handle_owned_writes, line)
        self.collect_handle_vector_updates(value.deferred_vector_updates, line)
        self.returned_handle_map_paths.update(dict.fromkeys(value.deferred_map_paths))
        if not value.pending_structure_complete and not value.deferred_map_paths:
            self.returned_handle_map_paths[()] = None
        alternatives = []
        if (not value.pending_structure_complete or value.deferred_field_updates
                or value.deferred_owned_updates or value.deferred_guarded_writes):
            alternatives.append((value.deferred_field_updates, value.deferred_owned_updates,
                                 (), value.deferred_definite_fields))
        for token in value.pending_structure_calls:
            if token not in self.pending:
                self.returned_handle_fields = None
                return
            name, actuals = self.pending[token]
            summary = self.effects.infer(name)
            if not summary.complete:
                self.returned_handle_fields = None
                return
            paths = completion_hashmap_writes(self.effects.definitions[name], summary)
            self.returned_handle_map_paths.update(dict.fromkeys(self.map_return_paths(
                paths or ((),), actuals, self.pending_map_keys[token])))
            vectors = summary.completion_result
            if any(summary.parameters[index][2] in INLINE_VECTOR_ELEMENTS
                   for index, *_ in vectors.vector_writes) or vectors.vector_write_payloads:
                self.returned_handle_fields = None
                return
            self.collect_handle_vector_updates(self.instantiate_deferred_vectors(
                self.vector_update_sources(vectors.vector_writes), actuals), line)
            owned = self.instantiate_deferred_owned(summary.completion_result.owned_field_writes,
                                                    actuals, environment)
            self.collect_deferred_owned(owned, self.returned_handle_owned_writes, line)
            guarded_definite = self.collect_returned_guarded_fields(summary, actuals)
            if guarded_definite is None:
                self.returned_handle_fields = None
                return
            alternatives.append((self.instantiate_deferred_fields(summary.structure_fields, actuals),
                                 owned, guarded_definite,
                                 None if value.pending_structure_complete else frozenset()))
        for updates, owned, guarded_definite, proof in alternatives:
            definite = set(guarded_definite) if value.pending_structure_complete else set()
            for carrier, field, _ in owned:
                destinations = self.injected_parameters(borrowed_targets(carrier))
                if not destinations:
                    self.returned_handle_fields = None
                    return
                if len(destinations) == 1 and (proof is None or (carrier, field) in proof):
                    definite.add((next(iter(destinations)), field))
            for carrier, fields in updates:
                destinations = borrowed_targets(carrier)
                if not destinations or any(target.kind != 'parameter' or self.params[target.parameter][1] != 'mut'
                                           for target in destinations):
                    self.returned_handle_fields = None
                    return
                for target in destinations:
                    guarded = target.parameter in self.mutex_parameters
                    output = self.returned_handle_guarded_fields if guarded else self.returned_handle_fields
                    known = output.setdefault(target.parameter, {})
                    kinds = ('parameter',) if guarded else ('parameter', 'field_parameter', 'detached_field_parameter')
                    for field, sources in fields:
                        if not sources or any(source.kind not in kinds for source in sources):
                            self.returned_handle_fields = None
                            return
                        known[field] = known.get(field, frozenset()) | sources
                        if len(destinations) == 1 and (proof is None or (carrier, field) in proof):
                            definite.add((target.parameter, field))
            if self.returned_handle_definite_fields is None:
                self.returned_handle_definite_fields = definite
            else:
                self.returned_handle_definite_fields.intersection_update(definite)

    def collect_handle_vector_updates(self, updates, line):
        if any(not carrier.structure_origins or carrier.typ in INLINE_VECTOR_ELEMENTS
               for carrier, _ in updates):
            raise IncompleteStructureEffects('vecteur différé sans provenance de stockage représentée')
        self.collect_deferred_vectors(updates, self.returned_handle_vector_updates, line)

    def map_return_paths(self, paths, actuals, keys=()):
        def parameter(index):
            actual = actuals[index]
            targets = borrowed_targets(actual) if isinstance(actual, Value) else frozenset()
            if len(targets) != 1 or next(iter(targets)).kind != 'parameter':
                raise IncompleteStructureEffects('effet différé de collection sans paramètre de provenance unique')
            return next(iter(targets)).parameter

        def captured_key(key):
            if isinstance(key, int):
                return keys[key] if keys else None
            return key

        return tuple(tuple((parameter(table), captured_key(key),
                            parameter(value) if value is not None else None)
                           for table, key, value in path)
                     for path in paths)

    def nodes(self, nodes, environment, valued=False, shadows=None, expected_array=None):
        environment.setdefault(MAP_STATE, Value('collection_state', 'Void', deferred_map_paths=frozenset({()})))
        return super().nodes(nodes, environment, valued, shadows, expected_array)

    @staticmethod
    def record_completed_map_paths(environment, paths):
        if not any(paths):
            return
        initial = environment[MAP_STATE].deferred_map_paths
        # Keeping the last occurrence of each identical operation bounds
        # loop summaries. Unknown-key insertions still retain every source.
        def normalize(path):
            return tuple(reversed(tuple(dict.fromkeys(reversed(path)))))

        environment[MAP_STATE] = replace(environment[MAP_STATE], deferred_map_paths=frozenset(
            normalize(before + after) for before in initial for after in paths))

    @staticmethod
    def map_constant_key(expression):
        if expression[0] in ('int', 'bool', 'array_numeric_literal') and isinstance(expression[-1], int):
            return str(int(expression[-1]))
        return None

    @staticmethod
    def guarded_write_sources(writes):
        return tuple((index, ((field, frozenset({BorrowTarget('parameter', source)})),))
                     for index, field, source in writes)

    @staticmethod
    def injected_parameters(targets):
        if not targets or any(target.kind != 'parameter' for target in targets):
            return frozenset()
        return frozenset(target.parameter for target in targets)

    def record_returned_guarded_writes(self, updates):
        for carrier, fields in updates:
            destinations = self.injected_parameters(borrowed_targets(carrier))
            if not destinations or not destinations <= self.mutex_parameters.keys():
                return False
            for field, targets in fields:
                sources = self.injected_parameters(targets)
                if not sources or any(self.params[source][1] != 'ref' for source in sources):
                    return False
                self.returned_handle_guarded_writes.update(
                    (holder, field, source) for holder in destinations for source in sources)
        return True

    def collect_returned_guarded_fields(self, summary, actuals):
        writes = self.instantiate_deferred_fields(self.guarded_write_sources(summary.guarded_writes), actuals)
        if not self.record_returned_guarded_writes(writes):
            return None
        definite = set()
        for carrier, fields in self.instantiate_deferred_fields(summary.guarded_fields, actuals):
            destinations = self.injected_parameters(borrowed_targets(carrier))
            if not destinations or not destinations <= self.mutex_parameters.keys():
                return None
            for holder in destinations:
                known = self.returned_handle_guarded_fields.setdefault(holder, {})
                for field, sources in fields:
                    if not sources or any(source.kind != 'parameter' for source in sources):
                        return None
                    known[field] = known.get(field, frozenset()) | sources
                    if len(destinations) == 1:
                        definite.add((holder, field))
        return definite

    def completed_value(self, mode, typ, values, *, joined=False, storage=None):
        if mode in ('ref', 'mut'):
            from numeric_core import numeric_type
            if not numeric_type(typ):
                raise IncompleteStructureEffects('résultat emprunté agrégé non raccordé aux effets de champs')
            value = Value(mode, typ,
                reference_targets=frozenset(target for value in values for target in value.reference_targets),
                payload_reference=any(value.payload_reference for value in values))
        elif mode in ('owned', 'join_owned', 'join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES, 'handle_option', 'buffered_handle_exchange', *UTF8_BORROW_MODES):
            if (not values and not joined) or any((value.mode, value.typ) != (mode, typ) for value in values):
                raise IncompleteStructureEffects('résultat async sans contrat de provenance compatible')
            # All complete child summaries can prove that no successful poll
            # returns. A launched handle still has the LaunchFailed exit, but
            # it carries no payload origin. Unknown summaries are rejected by
            # the caller before reaching this point, never treated as failure.
            value = merge_owned_values(values) if values else Value(mode, typ, absent_owned_payload=True)
        elif mode == 'async_execution':
            value = Value(mode, typ, deferred_field_updates=frozenset(
                update for value in values for update in value.deferred_field_updates),
                deferred_guarded_writes=frozenset(update for value in values for update in value.deferred_guarded_writes),
                deferred_owned_updates=merge_task_owned_updates(values, 'deferred_owned_updates'),
                deferred_vector_updates=frozenset(update for value in values for update in value.deferred_vector_updates),
                deferred_map_paths=merge_deferred_map_paths(values),
                deferred_definite_fields=merge_deferred_definite_fields(values))
        elif mode in FIELD_RESULT_MODES:
            # Plain scalars/arrays and error envelopes carry no memory target.
            value = Value(mode, typ)
        else:
            raise IncompleteStructureEffects('origine du résultat async non raccordée aux effets de champs')
        if not joined:
            return value
        if mode == 'buffered_handle_exchange' or mode in EXCHANGE_JOIN_TYPES:
            outer = exchange_join_mode(typ if mode == 'buffered_handle_exchange' else EXCHANGE_JOIN_TYPES[mode])
            return replace(value, mode=outer, typ=exchange_payload_type(outer))
        if mode in OPTION_JOIN_TYPES:
            return replace(value, mode=option_join_mode(OPTION_JOIN_TYPES[mode]))
        if mode in OWNED_JOIN_TYPES:
            return replace(value, mode=owned_join_mode(mode))
        if mode == 'handle_option':
            return replace(value, mode=option_join_mode(f'Option<{typ}>' if storage == 'local' else f'Option<A<{typ}>>'))
        if mode in ('owned', 'join_owned'):
            return replace(value, mode={'owned': 'join_owned', 'join_owned': 'join_nested'}[mode])
        if mode in ('ref', 'mut', *UTF8_BORROW_MODES):
            return replace(value, mode='join_' + mode)
        if mode == 'array':
            return replace(value, mode='join_array')
        if mode == 'async_execution':
            return replace(value, mode='join_async_execution')
        if f'join_{mode}' in NUMERIC_JOIN_FIELDS:
            return replace(value, mode=f'join_{mode}')
        if (plain := PLAIN_RETURN_JOINS.get((mode, typ))) is not None:
            return Value(plain, PLAIN_JOIN_TYPES[plain])
        if mode in ('join_nested', 'join_option', *EXCHANGE_JOIN_TYPES, *OPTION_JOIN_TYPES, *OWNED_JOIN_TYPES):
            raise IncompleteStructureEffects('troisième enveloppe propriétaire non raccordée')
        if mode in ('text', 'byte_ref', 'runtime_error'):
            return Value('join_' + mode, typ)
        return Value({'Int': 'join_int', 'Bool': 'join_bool', 'bool': 'join_bool',
                      'u8': 'join_byte', 'char': 'join_char'}.get(typ, 'join_void'), typ)

    def check_call_actuals(self, name, actuals, line):
        if any(isinstance(value, Value) and value.pending_structure_calls for value in actuals):
            summary = self.analyzer.infer(name)
            forwarding_execution = summary.task_forward_only and all(
                value.mode == 'execution' for value in actuals
                if isinstance(value, Value) and value.pending_structure_calls)
            if summary.mode == 'execution' and not forwarding_execution:
                raise IncompleteStructureEffects(
                    'effets différés attendus ou lancés par un auxiliaire synchrone non raccordés')
            if summary.task_wait_parameters and (summary.structure_fields or summary.mode not in (
                    'scalar', 'bool', 'byte', 'char', 'void')):
                raise IncompleteStructureEffects(
                    'ordre des écritures ou résultat emprunté de l’auxiliaire attendant non raccordé')
            # Relaying an already launched handle does not run or wait for it.
            # Its pending completion effects remain attached to the result.
            # A synchronous relay may transfer or discard an inactive input.
            # Neither operation runs its body. Pure forwarding preserves the
            # pending capture snapshots in ResultContext; a fresh alternative
            # stays unknown until its suspension contract is available.

    def apply_deferred_field_updates(self, task, environment, line):
        super().apply_deferred_field_updates(task, environment, line)
        if task.deferred_map_paths:
            self.record_completed_map_paths(environment, task.deferred_map_paths | {()})
        if not task.pending_structure_calls:
            return
        # A synchronous helper can explicitly consume a launched handle in
        # native code. Its contract records the wait, while this context owns
        # the original capture snapshots. LaunchFailed keeps the input state.
        branches = [({'next'}, environment.copy())]
        for token in task.pending_structure_calls:
            if token not in self.pending:
                raise IncompleteStructureEffects('attente sans contrat différé de champs')
            name, actuals = self.pending[token]
            summary = self.effects.infer(name)
            if not summary.complete:
                raise IncompleteStructureEffects(summary.reason)
            if summary.may_complete:
                branch, _ = self.apply_async_result(name, summary.parameters,
                    summary.completion_result, actuals, environment, line, 'completion')
                branches.append(({'next'}, branch))
        self.join_environments(environment, branches)

    def select_task_names(self, task):
        if not isinstance(task, Value) or task.mode != 'task':
            raise IncompleteStructureEffects('Select exige des instances async inactives aux captures identifiables')
        if not task.pending_structure_calls and task.typ in self.effects.definitions:
            return {task.typ}
        return {self.pending[token][0] for token in task.pending_structure_calls}

    def select_candidates(self, task):
        self.select_task_names(task)
        if not task.pending_structure_calls:
            summary = self.effects.infer(task.typ)
            if (task.deferred_suspension_updates is None or task.task_may_suspend is None
                    or task.deferred_suspension_owned is None or not summary.complete):
                raise IncompleteStructureEffects('effets de fabrique dans Select non raccordés')
            return [(task.typ, task, replace(summary, may_suspend=task.task_may_suspend))]
        candidates = []
        for token in task.pending_structure_calls:
            name, actuals = self.pending[token]
            summary = self.effects.infer(name)
            if not summary.complete or not summary.suspension_complete:
                raise IncompleteStructureEffects(summary.reason or summary.suspension_reason)
            candidates.append((name, actuals, summary))
        return candidates

    def apply_select_result(self, name, actuals, summary, environment, line, phase):
        if isinstance(actuals, Value):
            branch = environment.copy()
            if phase == 'suspension':
                self.apply_deferred_owned(actuals.deferred_suspension_owned, branch)
                self.apply_factory_fields(actuals.deferred_suspension_updates, branch, line)
                return branch, VOID
            _, completed = self.complete_factory(actuals, branch, line)
            return branch, completed
        return self.apply_async_result(name, summary.parameters,
            summary.suspension_result if phase == 'suspension' else summary.completion_result,
            actuals, environment, line, phase)

    def select_partial_states(self, candidates, environment, line, *, unpolled=True, suspended=True):
        """A loser may not have been polled; never substitute its final writes."""
        alternatives = [({'next'}, environment.copy())] if unpolled else []
        for name, actuals, summary in candidates:
            if suspended and summary.may_suspend:
                blocks = self.blocks
                self.blocks = [(outer.copy(), shadows.copy()) for outer, shadows in blocks]
                try:
                    branch, _ = self.apply_select_result(name, actuals, summary,
                        environment, line, 'suspension')
                finally:
                    self.blocks = blocks
                alternatives.append(({'next'}, branch))
        merged = environment.copy()
        self.join_environments(merged, alternatives)
        return merged

    def await_selection(self, selection, environment, line):
        signatures, exits, values = set(), [], []
        for token in selection.pending_structure_calls:
            branches, unreachable = [], False
            for task in self.selections[token]:
                candidates = [] if unreachable else self.select_candidates(task)
                branches.append(candidates)
                if candidates and all(not summary.may_suspend for _, _, summary in candidates):
                    # This branch either returns Ready or never yields control;
                    # in either case later branches cannot be polled.
                    unreachable = True
            signatures.update(self.effects.definitions[name].args[2]
                              for candidates in branches for name, _, _ in candidates)
            if len(signatures) != 1:
                raise IncompleteStructureEffects('Select exige le même type de résultat dans chaque branche')
            # Pending is possible only if every branch can suspend. An
            # immediately ready branch prevents an outward suspension.
            if all(any(summary.may_suspend for _, _, summary in candidates) for candidates in branches):
                partial = environment.copy()
                for candidates in branches:
                    partial = self.select_partial_states(candidates, partial, line, unpolled=False)
                self.observe_suspension(partial, line)
            for winner, candidates in enumerate(branches):
                if any(not any(summary.may_suspend for _, _, summary in earlier)
                       for earlier in branches[:winner]):
                    continue
                for name, actuals, summary in candidates:
                    if not summary.may_complete:
                        continue
                    branch, value = self.apply_select_result(name, actuals, summary,
                        environment, line, 'completion')
                    for index, losers in enumerate(branches):
                        if index != winner:
                            branch = self.select_partial_states(losers, branch, line,
                                unpolled=index > winner,
                                suspended=index < winner or bool(summary.may_suspend))
                    exits.append(({'next'}, branch))
                    values.append(value)
        if not exits:
            return set(), VOID
        self.join_environments(environment, exits)
        mode, typ = signatures.pop()
        return {'next'}, self.completed_value(mode, typ, values)

    def expression(self, expr, environment, line, expected_array=None, *, call_site=None):
        if expr is None:
            return super().expression(expr, environment, line, expected_array)
        op = expr[0]
        if op in ('array_mutex_lock', 'array_mutex_acquire') and expr[2][0] == 'name':
            receiver = environment.get(expr[2][1])
            if isinstance(receiver, Value) and any(
                    receiver.storage_owner == f'\0structure:{index}' for index in self.mutex_parameters):
                if op == 'array_mutex_acquire':
                    self.observe_suspension(environment, line)
                return {'next'}, replace(receiver, mode='owned', typ=expr[1])
        if op == 'reborrow' and isinstance(guard := environment.get(expr[1]), Value):
            if mutex_payload(guard.typ, GUARD_TYPES) and guard.storage_owner in environment:
                return {'next'}, replace(environment[guard.storage_owner], mode=expr[2])
        if op == 'task_select':
            flow, branches, signatures = {'next'}, [], set()
            for argument in expr[1]:
                if 'next' not in flow:
                    return flow, VOID
                part, task = self.expression(argument, environment, line)
                flow = (flow - {'next'}) | part
                if 'next' not in flow:
                    return flow, VOID
                signatures.update(self.effects.definitions[name].args[2] for name in self.select_task_names(task))
                if len(signatures) != 1:
                    raise IncompleteStructureEffects('Select exige le même type de résultat dans chaque branche')
                branches.append(task)
            token = (id(expr), tuple(branches))
            self.selections[token] = tuple(branches)
            mode, typ = signatures.pop()
            return flow, Value('selection', f'Select<{mode}:{typ}>', pending_structure_calls=frozenset({token}))
        if op == 'task_spawn':
            # Completion contracts alone cannot bound concurrently running
            # prefixes. Keep normal completion usable, but never report an
            # empty suspension contract for this unsupported composition.
            self.suspension_reason = 'effets suspendus de tâches lancées non raccordés'
        if op == 'call' and expr[1] in self.effects.definitions:
            definition = self.effects.definitions[expr[1]]
            if len(expr[2]) != len(definition.args[1]):
                self.fail(line, 'contrat async : nombre d’arguments incompatible')
            actuals = []
            flow = {'next'}
            for argument in expr[2]:
                if 'next' not in flow:
                    return flow, VOID
                part, value = self.expression(argument, environment, line)
                flow = (flow - {'next'}) | part
                actuals.append(value)
            # Stable under loop re-analysis; copies of a task descriptor keep
            # the same captures instead of looking up possibly shadowed names.
            token = (id(expr), tuple(actuals))
            self.pending[token] = (expr[1], tuple(actuals))
            self.pending_map_keys[token] = tuple(self.map_constant_key(arg) for arg in expr[2])
            return flow, Value('task', expr[1], pending_structure_calls=frozenset({token}),
                               pending_structure_complete=True)
        if op in ('await', 'task_join', 'task_join_value'):
            operand = ('name', expr[1]) if op == 'task_join' else expr[1]
            flow, task = self.expression(operand, environment, line)
            if 'next' not in flow:
                return flow, VOID
            if isinstance(task, Value) and task.mode == 'async_execution':
                from handle_types import public_async_signature
                signature = public_async_signature(task.typ, self.analyzer.enums, allow_borrowed=True)
                if op != 'await' or signature is None:
                    raise IncompleteStructureEffects('attente de paramètre AsyncHandle incompatible')
                self.observe_suspension(environment, line)
                self.suspension_reason = 'effets suspendus de tâches lancées non raccordés'
                self.apply_deferred_field_updates(task, environment, line)
                if signature[0] in ('ref', 'mut'):
                    return flow, Value('join_' + signature[0], signature[1],
                                       reference_targets=task.reference_targets)
                return flow, self.completed_value(*signature, (), joined=True)
            if isinstance(task, Value) and task.mode == 'selection':
                if op != 'await':
                    raise IncompleteStructureEffects('Select s’attend avec .await, pas join()')
                part, value = self.await_selection(task, environment, line)
                return (flow - {'next'}) | part, value
            if isinstance(task, Value) and task.mode == 'task' and not task.pending_structure_calls:
                # The factory contract carries suspended prefixes independently
                # of completion writes; neither takes effect at creation.
                self.observe_factory_suspensions(task, environment, line)
                part, completed = self.complete_factory(task, environment, line)
                return (flow - {'next'}) | part, completed
            if isinstance(task, Value) and task.mode == 'execution' and (
                    task.deferred_field_updates or not task.pending_structure_calls
                    and task.typ in self.effects.definitions and self.effects.infer(task.typ).complete):
                self.suspension_reason = 'effets suspendus de fabrique synchrone non raccordés'
                # A synchronous factory already mapped the deferred contract
                # onto these captured inputs. No synchronous body is available.
                temporary = '\0factory_execution'
                environment[temporary] = task
                try:
                    part, completed = super().expression(('task_join', temporary), environment, line)
                finally:
                    environment.pop(temporary)
                return (flow - {'next'}) | part, completed
            if not isinstance(task, Value) or task.mode not in ('task', 'execution') or not task.pending_structure_calls:
                raise IncompleteStructureEffects('attente sans captures de champs identifiables')
            branches = []
            completed_values = []
            if task.mode == 'execution':
                # LaunchFailed executes no body. Until the caller discriminates
                # the status, both original and completed field states survive.
                branches.append(({'next'}, environment.copy()))
            for token in task.pending_structure_calls:
                if token not in self.pending:
                    raise IncompleteStructureEffects('attente sans contrat différé de champs')
                name, actuals = self.pending[token]
                summary = self.effects.infer(name)
                if not summary.complete:
                    raise IncompleteStructureEffects(summary.reason)
                self.observe_child_suspensions(name, summary, actuals, environment, line)
                if not summary.may_complete:
                    continue
                inputs = environment
                if task.mode == 'task' and summary.handle_wait_order:
                    inputs = environment.copy()
                    temporary = '\0awaited_handle_capture'
                    for position in summary.handle_wait_order:
                        actual = actuals[position]
                        if not isinstance(actual, Value) or actual.mode != 'execution':
                            continue
                        inputs[temporary] = actual
                        part, _ = self.expression(('await', ('name', temporary)), inputs, line)
                        inputs.pop(temporary, None)
                        if 'next' not in part:
                            inputs = None
                            break
                    if inputs is None:
                        continue
                branch, completed = self.apply_async_result(name, summary.parameters,
                    summary.completion_result, actuals, inputs, line, 'completion')
                completed_values.append(completed)
                branches.append(({'next'}, branch))
            self.join_environments(environment, branches)
            if not branches:
                return flow - {'next'}, VOID
            signatures = {(*self.effects.definitions[self.pending[token][0]].args[2],
                           self.effects.definitions[self.pending[token][0]].join_storage_result)
                          for token in task.pending_structure_calls}
            if len(signatures) != 1:
                raise IncompleteStructureEffects('résultats différents dans un choix de tâches')
            mode, typ, storage = signatures.pop()
            # LaunchFailed contributes an unchanged environment, not a result
            # target. Only successful completions supply these payload values.
            return flow, self.completed_value(mode, typ, completed_values, joined=task.mode == 'execution', storage=storage)
        return super().expression(expr, environment, line, expected_array, call_site=call_site)
