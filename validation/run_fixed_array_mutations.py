"""Replay the fixed-array mutations in disposable copies; test oracles stay unchanged."""
import json, shutil, subprocess, sys, tempfile, hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
cases = [('borne supérieure',
  'crust.py',
  '{name} >= {length}',
  '{name} > {length}',
  'test_fixed_arrays.FixedArrayTests.test_nested_bounds_stop_before_column_or_rhs'),
 ('emprunts actifs',
  'crust.py',
  '        active = tuple(self.active_array_loans(after))',
  '        active = ()',
  'test_fixed_arrays.FixedArrayTests.test_dynamic_reference_swap_preserves_distinct_slots'),
 ('provenance de swap',
  'crust.py',
  '        holder.stored_array_loans = tuple(updated)\n'
  '        self.synchronize_array_container(holder)\n'
  '        base =',
  '        self.synchronize_array_container(holder)\n        base =',
  'test_fixed_arrays.FixedArrayTests.test_swap_stored_references_moves_provenance'),
 ('perte de la réservation entre cases',
  'crust.py',
  '                if any(loan.array_case_aliasing for loan in holder.stored_array_loans):',
  '                if False:',
  'test_fixed_arrays.FixedArrayTests.test_replacement_can_suspend_a_reference_in_another_slot'),
 ('perte de la mise à jour par alias',
  'array_syntax.py',
  '            environment[alias] = patch(value)',
  '            environment[alias] = value',
  'test_fixed_arrays.FixedArrayTests.test_alias_postcondition_prevents_reset_of_the_new_target'),
 ('perte de la génération précédente',
  'crust.py',
  '                        self.freeze_array_binding(target, received)',
  '                        pass',
  'test_fixed_arrays.FixedArrayTests.test_old_container_reborrow_updates_old_storage_after_rebinding'),
 ('dernier usage ignorant les éléments de la ligne référencée',
  'crust.py',
  '                selected = any(all(',
  '                selected = any(len(path) <= len(kind) and all(',
  'test_fixed_arrays.FixedArrayTests.test_stored_row_reference_bounds_and_whole_root_protection'),
 ('emprunts intérieurs non retenus',
  'crust.py',
  '                            yield child',
  '                            pass',
  'test_nested_reference_rows.NestedReferenceRowTests.test_nested_mutable_reborrow_suspends_and_restores_the_selected_leaf'),
 ('postconditions non propagées au stockage',
  'crust.py',
  '            self.synchronize_array_container(projected)',
  '            pass',
  'test_nested_reference_rows.NestedReferenceRowTests.test_nested_replace_returns_old_tree_and_installs_new_tree'),
 ('contenu récursif absent du contrat',
  'array_syntax.py',
  "        yield from reference_tree_fields(row, prefix + slot + '/')",
  '        pass',
  'test_nested_reference_rows.NestedReferenceRowTests.test_returned_reference_tree_keeps_container_and_leaf_sources'),
 ('dernier usage intérieur confondu avec celui de la ligne',
  'crust.py',
  '                        child_last = lifetimes.get(path, last)',
  '                        child_last = last',
  'test_nested_reference_rows.NestedReferenceRowTests.test_nested_leaf_last_use_allows_only_the_finished_pool'),
 ('mise à jour acceptée derrière une ligne partagée',
  'crust.py',
  "                    if loan.kind == 'array_ref' and same_container and old_roots != new_roots:",
  '                    if False:',
  'test_nested_reference_rows.NestedReferenceRowTests.test_opaque_contract_cannot_mutate_contents_through_shared_row'),
 ('projection intérieure non remappée',
  'array_syntax.py',
  '    if prototype.typ != typ and reference_array_shape(prototype.typ):',
  '    if False:',
  'test_nested_reference_rows.NestedReferenceRowTests.test_returned_inline_row_projection_updates_only_its_actual_slots'),
 ('effets des lignes injectées oubliés après transfert',
  'crust.py',
  '        for parameter, path, fields in summary.referent_fields:',
  '        for parameter, path, fields in ():',
  'test_nested_reference_rows.NestedReferenceRowTests.test_transferred_outer_container_preserves_writes_to_parent_rows'),
 ('remplacement de pointeur confondu avec écriture du référent',
  'array_syntax.py',
  '            if slot in old and old[slot].container_origins & row.container_origins:',
  '            if slot in old:',
  'test_nested_reference_rows.NestedReferenceRowTests.test_transferred_outer_container_preserves_writes_to_parent_rows')]

results=[]
for name, filename, before, after, test in cases:
    with tempfile.TemporaryDirectory(prefix='crust-nested-mutation-') as directory:
        folder=Path(directory)
        (folder/'tests').mkdir()
        shutil.copytree(root / 'prototype', folder / 'prototype',
                        ignore=shutil.ignore_patterns('__pycache__'))
        for copy in ('tests/test_fixed_arrays.py','tests/test_nested_reference_rows.py'):
            shutil.copyfile(root/copy,folder/copy)
        source = folder / 'prototype' / filename
        text=source.read_text()
        assert text.count(before)==1,(name,text.count(before))
        source.write_text(text.replace(before,after))
        done=subprocess.run([sys.executable, '-E', '-m', 'unittest', test],cwd=folder/'tests',capture_output=True,text=True,timeout=60)
        results.append(dict(mutation=name,source_file=filename,before=before,after=after,test=test,
            classification='detected' if done.returncode else 'survived',detected=done.returncode!=0,
            source_sha256=hashlib.sha256((root / 'prototype'/filename).read_bytes()).hexdigest(),log=done.stderr))
(root/'validation/fixed-array-current-mutations.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:v for k,v in row.items() if k not in ('log','before','after','source_sha256')} for row in results],ensure_ascii=False))
