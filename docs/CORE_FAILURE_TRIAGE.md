[Français](CORE_FAILURE_TRIAGE-fr.md)

<a id="tri-des-145-échecs-de-la-validation-générale"></a>

# Sorting of 145 failures of general validation

Original pass perimeter in [General Validation Report](cycles/ENUM_CORE_VALIDATION_CYCLE.md).
The sorting involves 145 distinct methods, many of which have sub-cases.
It combines the first block visible in the newspaper, the fixtures and rejeuners
representative in kernel syntax, with `numeric_core=True` and the profile of the
compatibility disabled. One row classified as "to migrate" may reveal another
default after migration. The language rules and compiler remain unchanged
in this sorting cycle.

<a id="corrections-du-noyau-confirmées"></a>

## Confirmed kernel fixes

- [x] **N4–N6, N8 and E6.** Preserving the coordinates of returned loans
  from an array by a task, then check the return via `.await` ou
  `join()`. The witness `&mut [i32; 2] -> &mut i32` causes
  `TypeError` in both compiler entries.
  shared and mixed rows also reproduced the failure.
  constant or dynamic indices, availability of other elements,
  the reservation until last use and `LaunchFailed`.
- [x] **N1, AS4 and runtime results.** Align the Boolean type in
  C produced for `match h.await`. The C tries to read a field
  `bool_value` The following are the most important examples of the following: `if` who chooses
  between a boolean result expected and a local boolean.
  `join()` simple on a Boolean result already prints `7`.
- [x] **N1 and V1.** Refuser l'annotation scalaire `let n: i32 = p.new(10)`
  The two entries accept it and the C shows that
  `n` the annotation remains dereferençable. `A<i32>` is the expected form.
  This defect was isolated during the sorting of the historical annotation test,
  whose claim failed concerned an old rule on `Int`.
- [x] **N1 and E4.** Give the right side literal the type of the element in
  writing async `row[0] = 12` on `&mut [i32; 2]`. The witness is refused
  Both entrances. `let n: i32 = 12; row[0] = n;`, the C print `12`.
  This defect appeared in migrant the subtable capture test,
  The expectation of the constant index named is a matter for the oracle.

The defects described above correspond to the initial condition of the sorting.
Corrected controls and re-played regressions are shown in
[CORE_INTEGRATION_FOLLOWUP_CYCLE.md](cycles/CORE_INTEGRATION_FOLLOWUP_CYCLE.md).

<a id="traitement-des-autres-familles"></a>

## Treatment of other families

- **Historical signatures and storage.** Parameter signatures or
  return must express `A<T>` when the object is in a pool. Remove
  transfer markers and migrate to kernel types. The replay of a
  `A<View>` with a borrowed field and a relay function succeeds. He refuses
  the transfer of the reborrowing before its last use.
- **Fixtures blocked by U1.** To make explicit use of the links of the
  positive scenario while preserving the cleaning points.
  Block output passes after this correction. Negative sub-cases must
  always reach the invariant they are supposed to exercise.
- **Reset and feature type.** Tests where the central operation is `reset()`
  The tests are compatible. `type feature` are separated from the
  target kernel. Cases classified by their first block also contain
  of reset in later variants.
- **Oracles.** Comparison of two `u8` passes according to the digital rules.
  A table capture with the index named constant `let i = 0` autorise
  access to another row. The witness with unknown clues is denied.
  A shared loan detached from an enum allows the destruction of the bearer
  when its target survives and blocks the destruction of this target.
  Some other assertions check internal C fragments or the
  text of a diagnosis. Revalidate properties at their observable level.
- **Cas mixtes.** The `Vector<A<T>>`, the pool alias of
  collection and field graph possessed in async require a replay
  The modern field graph indicator passes after the
  replacement of the target and return of the bearer.
- **Library.** The error type test of the `char_at` stops typing
  of the Literal `0`. An explicit variable `i32` permet d'atteindre
  The connection of the literal context for this API is
  distinct from memory kernel defects.

The repros and native results are in the
[Witness log](../validation/core-failure-triage.log). C compilations
witnesses use UBSan, `-O0` ou `-O2` according to the lot.
Don't replay the 145 methods one by one after full rewriting.

<a id="index-par-famille"></a>

## Index by family

Each link refers to the test method. Families are separated according to
the first block selected for sorting.


<a id="signatures-historiques-et-stockage-70"></a>

### Historical signatures and storage (70)

- [`test_async_consuming_enum_match.test_nested_owned_child_preserves_descendant_pool`](../tests/test_async_consuming_enum_match.py#L110)
- [`test_async_owned_enums.test_borrowed_field_return_keeps_target`](../tests/test_async_owned_enums.py#L81)
- [`test_async_owned_enums.test_conditional_variants_and_reference_targets`](../tests/test_async_owned_enums.py#L165)
- [`test_async_owned_enums.test_fresh_enum_from_injected_pool`](../tests/test_async_owned_enums.py#L50)
- [`test_async_owned_enums.test_owned_children_cleanup_on_inactive_and_launch_failure`](../tests/test_async_owned_enums.py#L91)
- [`test_async_owned_enums.test_owned_fields_of_inactive_variants_are_not_read`](../tests/test_async_owned_enums.py#L179)
- [`test_async_owned_enums.test_public_handle_and_relay_keep_reference_field`](../tests/test_async_owned_enums.py#L108)
- [`test_async_owned_enums.test_recorded_enum_and_variants`](../tests/test_async_owned_enums.py#L20)
- [`test_async_owned_enums.test_relay_and_consumption_in_sync_helper`](../tests/test_async_owned_enums.py#L30)
- [`test_async_owned_enums.test_select_borrowed_enum_fields_remain_live`](../tests/test_async_owned_enums.py#L151)
- [`test_async_owned_enums.test_select_winner_and_loser_reuse_model`](../tests/test_async_owned_enums.py#L61)
- [`test_async_owned_enums.test_sync_bridge_reads_only_active_variant`](../tests/test_async_owned_enums.py#L120)
- [`test_audit_regressions.test_enum_identity_preserves_arm_and_source`](../tests/test_audit_regressions.py#L111)
- [`test_borrowed_returns.test_basic_return_uses_parent_target_and_keeps_address`](../tests/test_borrowed_returns.py#L63)
- [`test_borrowed_returns.test_conditional_expression_in_function_propagates_borrow_targets`](../tests/test_borrowed_returns.py#L160)
- [`test_borrowed_returns.test_conditional_return_protects_each_possible_target`](../tests/test_borrowed_returns.py#L149)
- [`test_borrowed_returns.test_discarding_old_view_during_reassignment_releases_old_dependency`](../tests/test_borrowed_returns.py#L218)
- [`test_borrowed_returns.test_drop_mutation_and_move_before_returned_view_usage_rejected`](../tests/test_borrowed_returns.py#L73)
- [`test_borrowed_returns.test_empty_or_borrowed_variant_retains_conservative_dependency`](../tests/test_borrowed_returns.py#L172)
- [`test_borrowed_returns.test_empty_variant_and_forwarding_do_not_invent_borrow`](../tests/test_borrowed_returns.py#L166)
- [`test_borrowed_returns.test_forwarded_holder_preserves_mutable_reborrow_parent`](../tests/test_borrowed_returns.py#L49)
- [`test_borrowed_returns.test_holder_pool_can_reset_before_fresh_view_is_returned`](../tests/test_borrowed_returns.py#L235)
- [`test_borrowed_returns.test_independent_scope_route_model`](../tests/test_borrowed_returns.py#L256)
- [`test_borrowed_returns.test_last_use_allows_drop_and_slot_reuse`](../tests/test_borrowed_returns.py#L79)
- [`test_borrowed_returns.test_last_use_allows_reset`](../tests/test_borrowed_returns.py#L85)
- [`test_borrowed_returns.test_loop_future_usage_keeps_returned_dependency`](../tests/test_borrowed_returns.py#L224)
- [`test_borrowed_returns.test_make_view_contract_records_input_identity`](../tests/test_borrowed_returns.py#L34)
- [`test_borrowed_returns.test_mixed_fresh_and_input_variants_resolve_only_possible_fields`](../tests/test_borrowed_returns.py#L242)
- [`test_borrowed_returns.test_nested_block_can_transfer_holder_but_not_promote_local_target`](../tests/test_borrowed_returns.py#L127)
- [`test_borrowed_returns.test_nested_reset_preserves_read_before_reset_and_rejects_reset_before_read`](../tests/test_borrowed_returns.py#L196)
- [`test_borrowed_returns.test_opaque_call_needs_no_body_or_inference_tables`](../tests/test_borrowed_returns.py#L185)
- [`test_borrowed_returns.test_owned_holder_roundtrip_preserves_identity_and_dependencies`](../tests/test_borrowed_returns.py#L133)
- [`test_borrowed_returns.test_pending_returned_holder_protects_target_during_later_argument`](../tests/test_borrowed_returns.py#L209)
- [`test_borrowed_returns.test_plain_import_return_after_roundtrip_restores_only_holder`](../tests/test_borrowed_returns.py#L144)
- [`test_borrowed_returns.test_reset_of_holder_pool_ends_borrow_without_destroying_target`](../tests/test_borrowed_returns.py#L204)
- [`test_borrowed_returns.test_returned_shared_reborrow_suspends_then_restores_mutable_parent`](../tests/test_borrowed_returns.py#L40)
- [`test_borrowed_returns.test_shared_child_does_not_authorize_unrelated_alias_of_original_handle`](../tests/test_borrowed_returns.py#L56)
- [`test_borrowed_returns.test_successive_function_returns_preserve_borrow`](../tests/test_borrowed_returns.py#L90)
- [`test_borrowed_returns.test_successive_nested_blocks_verify_each_parent_boundary`](../tests/test_borrowed_returns.py#L229)
- [`test_borrowed_returns.test_temporary_referent_argument_belongs_to_caller_scope`](../tests/test_borrowed_returns.py#L213)
- [`test_conditional_returns.test_enum_arms_can_differ_but_enum_type_and_root_pool_are_identical`](../tests/test_conditional_returns.py#L121)
- [`test_direct_borrow_returns.test_returned_ref_stored_in_holder_protects_all_targets`](../tests/test_direct_borrow_returns.py#L150)
- [`test_drop_transitions.test_enum_replacement_does_not_revive_handle_or_borrow`](../tests/test_drop_transitions.py#L151)
- [`test_drop_transitions.test_enum_replacement_reuses_its_arm_without_affecting_other_arm`](../tests/test_drop_transitions.py#L120)
- [`test_effects.test_enum_field_effects_and_type_requirements`](../tests/test_effects.py#L100)
- [`test_fresh_recursive_factories.test_conditional_factory_keeps_each_returned_shape`](../tests/test_fresh_recursive_factories.py#L41)
- [`test_fresh_recursive_factories.test_new_graph_after_factory_and_relay`](../tests/test_fresh_recursive_factories.py#L21)
- [`test_fresh_recursive_factories.test_new_graph_from_factory_inside_async`](../tests/test_fresh_recursive_factories.py#L35)
- [`test_function_bodies.test_unused_enum_body_and_generic_source_forwarding`](../tests/test_function_bodies.py#L119)
- [`test_modular_calls.test_enum_pool_contracts_keep_type_and_provenance`](../tests/test_modular_calls.py#L203)
- [`test_modular_calls.test_generic_interface_allocation_requirements_are_still_checked`](../tests/test_modular_calls.py#L209)
- [`test_mutable_match.test_conditional_field_targets_are_conservative`](../tests/test_mutable_match.py#L106)
- [`test_mutable_match.test_transfer_function_reborrow_and_reset`](../tests/test_mutable_match.py#L79)
- [`test_mutable_match_escape.test_possible_arms_preserve_both_target_provenances`](../tests/test_mutable_match_escape.py#L53)
- [`test_mutable_match_reservations.test_stored_reservation_survives_opaque_owned_return`](../tests/test_mutable_match_reservations.py#L37)
- [`test_mutable_reference_fields.test_conditional_targets_all_protected`](../tests/test_mutable_reference_fields.py#L109)
- [`test_mutable_reference_fields.test_conditional_variants_keep_strongest_capability`](../tests/test_mutable_reference_fields.py#L131)
- [`test_mutable_reference_fields.test_forward_owned_holder`](../tests/test_mutable_reference_fields.py#L85)
- [`test_mutable_reference_fields.test_returned_holder_and_successive_calls`](../tests/test_mutable_reference_fields.py#L80)
- [`test_pool_requirements.test_enum_allocation_does_imply_pool_requirement`](../tests/test_pool_requirements.py#L116)
- [`test_provenances.test_enum_pool_root_matches_actual_arm_on_partial_reset`](../tests/test_provenances.py#L209)
- [`test_reassignment.test_enum_replacement_destroys_correct_arm_then_reuses_old_arm_slot`](../tests/test_reassignment.py#L138)
- [`test_recursive_join_helpers.test_async_caller_cannot_hide_blocking_join`](../tests/test_recursive_join_helpers.py#L51)
- [`test_recursive_join_helpers.test_join_result_keeps_deep_reference`](../tests/test_recursive_join_helpers.py#L26)
- [`test_recursive_join_helpers.test_recorded_public_handle_join`](../tests/test_recursive_join_helpers.py#L17)
- [`test_recursive_join_helpers.test_two_helpers_terminal_variant_and_launch_failure`](../tests/test_recursive_join_helpers.py#L36)
- [`test_recursive_task_factories.test_factory_and_task_relay_keep_descendant_variants`](../tests/test_recursive_task_factories.py#L12)
- [`test_recursive_task_factories.test_factory_preserves_recursive_stored_reference`](../tests/test_recursive_task_factories.py#L28)
- [`test_reference_values.test_named_field_initializer_preserves_the_same_target`](../tests/test_reference_values.py#L106)
- [`test_results.test_enum_identity_and_fresh_sources`](../tests/test_results.py#L223)

<a id="fixtures-bloquées-par-u1-29"></a>

### Fixtures blocked by U1 (29)

- [`test_audit_regressions.test_abrupt_later_initializer_does_not_publish_partial_enum`](../tests/test_audit_regressions.py#L50)
- [`test_audit_regressions.test_independent_cleanup_model_for_moves_returns_and_conditional_drops`](../tests/test_audit_regressions.py#L153)
- [`test_continue.test_function_return_after_restart_preserves_allocation`](../tests/test_continue.py#L90)
- [`test_continue.test_nested_cleanup_precedes_restart_and_pool_slot_is_reused`](../tests/test_continue.py#L20)
- [`test_drop_transitions.test_replacement_never_revives_old_handle`](../tests/test_drop_transitions.py#L94)
- [`test_foundation_rules.test_acyclic_enum_contract_resolves_only_reachable_reference_paths`](../tests/test_foundation_rules.py#L2311)
- [`test_foundation_rules.test_byte_slice_index_tracks_reference_but_copies_the_value`](../tests/test_foundation_rules.py#L9548)
- [`test_foundation_rules.test_explicit_allocation_annotation_rejects_other_storage_and_types`](../tests/test_foundation_rules.py#L10220)
- [`test_foundation_rules.test_mutable_match_joins_projection_and_external_borrow`](../tests/test_foundation_rules.py#L6096)
- [`test_foundation_rules.test_shared_match_transfers_allocation_and_cleans_other_local`](../tests/test_foundation_rules.py#L6185)
- [`test_foundation_rules.test_shared_reference_vector_empty_contract_preserves_call_and_alternatives`](../tests/test_foundation_rules.py#L4620)
- [`test_foundation_rules.test_shared_reference_vector_mutable_parameter_publishes_targets`](../tests/test_foundation_rules.py#L4887)
- [`test_foundation_rules.test_shared_structure_parameter_tracks_nested_detached_borrow`](../tests/test_foundation_rules.py#L2269)
- [`test_foundation_rules.test_string_merge_rejects_missing_move_alias_and_reuse`](../tests/test_foundation_rules.py#L9181)
- [`test_foundation_rules.test_vector_try_extend_accepts_scoped_byte_slice`](../tests/test_foundation_rules.py#L9415)
- [`test_scope_exit.test_allocation_return_excludes_result_from_child_cleanup`](../tests/test_scope_exit.py#L51)
- [`test_scope_exit.test_explicit_drop_is_not_repeated_during_unwinding`](../tests/test_scope_exit.py#L60)
- [`test_scope_exit.test_local_sources_close_while_external_result_survives`](../tests/test_scope_exit.py#L75)
- [`test_scope_exit.test_normal_exit_closes_only_inner_scopes`](../tests/test_scope_exit.py#L30)
- [`test_scope_exit.test_reception_order_is_preserved_during_return`](../tests/test_scope_exit.py#L66)
- [`test_scope_exit.test_scalar_return_cleans_before_caller_continues`](../tests/test_scope_exit.py#L44)
- [`test_scope_exit.test_unreachable_allocations_have_no_generated_cleanup`](../tests/test_scope_exit.py#L92)
- [`test_scope_exit.test_void_return_closes_all_function_scopes`](../tests/test_scope_exit.py#L37)
- [`test_while.test_condition_effects_are_visible_even_when_false`](../tests/test_while.py#L104)
- [`test_while.test_condition_is_rechecked_after_continue_and_fallthrough`](../tests/test_while.py#L36)
- [`test_while.test_condition_temporary_survives_until_iteration_cleanup`](../tests/test_while.py#L59)
- [`test_while.test_nested_loop_targets_and_private_source_cleanup`](../tests/test_while.py#L112)
- [`test_while.test_owned_function_return_from_body`](../tests/test_while.py#L119)
- [`test_while.test_return_during_condition_cleans_function`](../tests/test_while.py#L130)

<a id="core--résultat-booléen-async-6"></a>

### Core — async boolean result (6)

- [`test_async_runtime.test_async_bool_control_results_preserve_branch_type`](../tests/test_async_runtime.py#L9271)
- [`test_async_runtime.test_threaded_bool_result_preserves_type_in_ok_branch`](../tests/test_async_runtime.py#L9239)
- [`test_nested_plain_results.test_payload_depth_and_capture_matrix`](../tests/test_nested_plain_results.py#L57)
- [`test_plain_join_contracts.test_plain_results_capture_by_value_and_survive_suspension`](../tests/test_plain_join_contracts.py#L98)
- [`test_public_handle_types.test_result_type_matrix_sync_and_async`](../tests/test_public_handle_types.py#L16)
- [`test_sync_bool_calls.test_named_annotated_mutated_and_native_captured_bool`](../tests/test_sync_bool_calls.py#L36)

<a id="core--projections-de-tableaux-retournées-en-async-13"></a>

### Core — projections of tables returned in async (13)

- [`test_async_runtime.test_async_capture_follows_referenced_rows`](../tests/test_async_runtime.py#L3870)
- [`test_async_runtime.test_async_join_preserves_nested_reference_coordinates`](../tests/test_async_runtime.py#L3789)
- [`test_async_runtime.test_async_mixed_reference_rows_respect_shared_boundaries`](../tests/test_async_runtime.py#L3929)
- [`test_async_runtime.test_factory_returns_task_borrowing_array_parameter`](../tests/test_async_runtime.py#L3304)
- [`test_async_runtime.test_join_projects_result_from_reference_row`](../tests/test_async_runtime.py#L3683)
- [`test_async_runtime.test_sync_function_joins_handle_returning_array_element`](../tests/test_async_runtime.py#L9368)
- [`test_async_runtime.test_sync_function_returns_joined_array_reference`](../tests/test_async_runtime.py#L9399)
- [`test_async_runtime.test_sync_join_borrow_can_choose_inline_or_pool_storage`](../tests/test_async_runtime.py#L3194)
- [`test_async_runtime.test_sync_join_returns_an_inline_array_element`](../tests/test_async_runtime.py#L3154)
- [`test_async_runtime.test_sync_join_returns_stored_reference_through_contract`](../tests/test_async_runtime.py#L3725)
- [`test_async_runtime.test_sync_nested_int_array_capture_preserves_storage_and_projection`](../tests/test_async_runtime.py#L4169)
- [`test_async_runtime.test_sync_recaptures_joined_array_reference_by_name`](../tests/test_async_runtime.py#L9462)
- [`test_concrete_handle_relays.test_reference_row_result_sources`](../tests/test_concrete_handle_relays.py#L230)

### Profil historique — reset (3)

- [`test_foundation_rules.test_constraints_keep_possible_match_field_at_conditional_join`](../tests/test_foundation_rules.py#L6037)
- [`test_foundation_rules.test_shared_reference_vector_contract_preserves_literal_slot`](../tests/test_foundation_rules.py#L4579)
- [`test_sync_handle_fields.test_field_result_reset_contract_without_bodies`](../tests/test_sync_handle_fields.py#L112)

### Profil hors core — type feature (1)

- [`test_type_features.test_declaration_storage_and_signature_rejections`](../tests/test_type_features.py#L88)

<a id="oracles-et-attentes-à-réviser-16"></a>

### Oracles and expectations to be revised (16)

- [`test_async_runtime.test_async_local_byte_survives_yield_and_keeps_lexical_type`](../tests/test_async_runtime.py#L4336)
- [`test_async_runtime.test_sync_tableau_capture_survives_spawn_and_releases_at_join`](../tests/test_async_runtime.py#L3101)
- [`test_cell_reference_bridges.test_generated_bridge_can_replace_an_external_field_with_cell_input`](../tests/test_cell_reference_bridges.py#L180)
- [`test_foundation_rules.test_allocation_annotation_checks_type_without_changing_storage`](../tests/test_foundation_rules.py#L6488)
- [`test_foundation_rules.test_consuming_handle_method_keeps_pool_contract_and_address`](../tests/test_foundation_rules.py#L7701)
- [`test_foundation_rules.test_match_expression_returns_typed_shared_projection`](../tests/test_foundation_rules.py#L2835)
- [`test_foundation_rules.test_match_returns_typed_borrow_from_each_possible_carrier`](../tests/test_foundation_rules.py#L2703)
- [`test_foundation_rules.test_mutable_match_can_return_shared_field`](../tests/test_foundation_rules.py#L6144)
- [`test_foundation_rules.test_named_byte_slice_holds_the_source_until_last_use`](../tests/test_foundation_rules.py#L9449)
- [`test_foundation_rules.test_recursive_handle_field_layout_is_pointer_sized`](../tests/test_foundation_rules.py#L732)
- [`test_foundation_rules.test_struct_methods_do_not_shadow_storage_or_int_operations`](../tests/test_foundation_rules.py#L7775)
- [`test_foundation_rules.test_utf8_index_rejects_type_confusion_and_mutable_access`](../tests/test_foundation_rules.py#L8089)
- [`test_foundation_rules.test_utf8_literals_reject_invalid_escape_and_int_coercion`](../tests/test_foundation_rules.py#L8056)
- [`test_inline_struct_vectors.test_payload_copy_survives_vector_and_pool`](../tests/test_inline_struct_vectors.py#L18)
- [`test_suspension_effects.test_generated_select_loser_keeps_last_write_not_restoration`](../tests/test_suspension_effects.py#L210)
- [`test_utf8_try_slice.test_rejects_dangling_result_mutation_and_unused_results`](../tests/test_utf8_try_slice.py#L203)

<a id="cas-mixtes-à-migrer-puis-à-rejouer-6"></a>

### Mixed cases to migrate and replay (6)

- [`test_async_pool_aliases.test_collection_alias_sources_and_reuse`](../tests/test_async_pool_aliases.py#L111)
- [`test_foundation_rules.test_handle_replacement_builds_vector_slots_in_callee`](../tests/test_foundation_rules.py#L11058)
- [`test_foundation_rules.test_handle_replacement_builds_vector_with_conditional_inventory`](../tests/test_foundation_rules.py#L11150)
- [`test_foundation_rules.test_handle_replacement_transports_transformed_vector_inventory`](../tests/test_foundation_rules.py#L11098)
- [`test_foundation_rules.test_mutable_handle_replacement_transfers_vector_slots`](../tests/test_foundation_rules.py#L11028)
- [`test_nested_field_replacement.test_async_changes_owned_graph_and_returns_it`](../tests/test_nested_field_replacement.py#L80)

<a id="bibliothèque--indice-de-char_at-1"></a>

### Library — char_at index (1)

- [`test_spawn_blocking.test_public_runtime_error_in_owned_and_nested_result_contracts`](../tests/test_spawn_blocking.py#L89)
