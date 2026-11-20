# Test report

Run: 2026-11-08 19:07. Command: `uv run pytest` against a fresh `pharmatrace_test` database.

Summary: 68 of 68 automated tests passed.

## Lab-manual test cases

| TC ID | Test | Automated test(s) | Actual result | Status |
|---|---|---|---|---|
| TC01 | Register a valid product | test_tc01_valid_product_saved | As expected | Pass |
| TC02 | Invalid temperature range rejected | test_tc02_invalid_temperature_range_rejected | As expected | Pass |
| TC03 | Duplicate batch number rejected | test_tc03_duplicate_batch_number_rejected | As expected | Pass |
| TC04 | Expiry before manufacture rejected | test_tc04_expiry_before_manufacture_rejected | As expected | Pass |
| TC05 | Quantity boundary (0 rejected, 1 accepted) | test_tc05_quantity_boundary | As expected | Pass |
| TC06 | Product with batches cannot be deleted | test_tc06_product_with_batches_cannot_be_deleted | As expected | Pass |
| TC07 | Shipment with nonexistent vehicle rejected | test_tc07_nonexistent_vehicle_rejected | As expected | Pass |
| TC08 | Same origin and destination rejected | test_tc08_same_origin_and_destination_rejected | As expected | Pass |
| TC09 | Add batch to shipment | test_tc09_add_batch_to_shipment | As expected | Pass |
| TC10 | Same batch twice in a shipment rejected | test_tc10_same_batch_twice_rejected | As expected | Pass |
| TC11 | Dispatch records movements, checkpoint and status | test_tc11_dispatch_records_movements_checkpoint_and_status | As expected | Pass |
| TC12 | Partial failure rolls back the whole dispatch | test_tc12_partial_failure_rolls_back_everything | As expected | Pass |
| TC13 | Expired or quarantined batch cannot be dispatched | test_tc13_expired_batch_cannot_be_dispatched, test_tc13_quarantined_batch_cannot_be_dispatched | As expected | Pass |
| TC14 | Concurrent dispatches cannot oversell stock | test_tc14_concurrent_dispatches_cannot_oversell | As expected | Pass |
| TC15 | Receive moves stock and closes sensor assignment | test_tc15_receive_moves_stock_and_closes_assignment | As expected | Pass |
| TC16 | Overlapping sensor assignment rejected | test_tc16_overlapping_sensor_assignment_rejected | As expected | Pass |
| TC17 | Valid in-range reading, no incident | test_tc17_valid_reading_in_range_no_incident | As expected | Pass |
| TC18 | Out-of-limit reading creates and links an incident | test_tc18_out_of_limit_reading_creates_incident | As expected | Pass |
| TC19 | Repeated breach appends to the same incident | test_tc19_repeated_breach_appends_and_escalates | As expected | Pass |
| TC20 | Duplicate reading rejected | test_tc20_duplicate_reading_rejected | As expected | Pass |
| TC21 | Future timestamp stored as invalid, no incident | test_tc21_future_timestamp_stored_as_invalid_without_incident | As expected | Pass |
| TC22 | Gap in readings appears in data-quality report | test_tc22_gap_appears_in_quality_report | As expected | Pass |
| TC23 | Original reading values protected | test_tc23_original_reading_values_are_protected | As expected | Pass |
| TC24 | Only breached batches linked to incident | test_tc24_only_breached_batches_are_linked | As expected | Pass |
| TC25 | Wrong password rejected | test_tc25_wrong_password_rejected | As expected | Pass |
| TC26 | Unauthorised status change rejected (API and DB) | test_tc26_operator_cannot_change_batch_status, test_tc26_database_rule_applies_even_to_allowed_api_roles, test_tc26_operator_cannot_release_batch | As expected | Pass |
| TC27 | SQL injection treated as plain text | test_tc27_sql_injection_is_plain_text | As expected | Pass |
| TC28 | App role cannot delete readings or write audit log | test_tc28_app_role_cannot_delete_readings_or_audit | As expected | Pass |
| TC29 | Complete an investigation (findings required) | test_tc29_complete_investigation_requires_findings | As expected | Pass |
| TC30 | Close blocked by pending action / unassessed batch | test_tc30_cannot_close_with_pending_action_or_unassessed_batch | As expected | Pass |
| TC31 | Close a fully resolved incident (QM only, audited) | test_tc31_close_fully_resolved_incident | As expected | Pass |
| TC32 | Dashboard counts match base tables | test_tc32_dashboard_matches_base_tables | As expected | Pass |
| TC33 | Incident report totals match | test_tc33_incident_report_totals_match | As expected | Pass |
| TC34 | Form validation messages | test_tc34_validation_messages | As expected | Pass |

## All automated tests

| File | Test | Result | Time (s) |
|---|---|---|---|
| test_api | test_tc25_wrong_password_rejected | Pass | 2.98 |
| test_api | test_requests_need_a_token | Pass | 0.20 |
| test_api | test_tc26_operator_cannot_change_batch_status | Pass | 0.26 |
| test_api | test_tc26_database_rule_applies_even_to_allowed_api_roles | Pass | 0.26 |
| test_api | test_tc27_sql_injection_is_plain_text | Pass | 0.28 |
| test_api | test_tc34_validation_messages | Pass | 0.29 |
| test_api | test_db_errors_become_readable_responses | Pass | 0.29 |
| test_api | test_end_to_end_incident_workflow | Pass | 0.65 |
| test_api | test_reports_and_dashboard_available | Pass | 0.32 |
| test_api | test_admin_only_endpoints | Pass | 0.39 |
| test_api | test_owner_sees_hashes_not_in_api | Pass | 0.18 |
| test_db_constraints | test_tc01_valid_product_saved | Pass | 0.08 |
| test_db_constraints | test_tc02_invalid_temperature_range_rejected | Pass | 0.09 |
| test_db_constraints | test_humidity_limits_must_come_in_pairs | Pass | 0.06 |
| test_db_constraints | test_tc03_duplicate_batch_number_rejected | Pass | 0.13 |
| test_db_constraints | test_tc04_expiry_before_manufacture_rejected | Pass | 0.13 |
| test_db_constraints | test_tc05_quantity_boundary | Pass | 0.12 |
| test_db_constraints | test_tc06_product_with_batches_cannot_be_deleted | Pass | 0.10 |
| test_db_constraints | test_tc07_nonexistent_vehicle_rejected | Pass | 0.12 |
| test_db_constraints | test_tc08_same_origin_and_destination_rejected | Pass | 0.12 |
| test_db_constraints | test_tc09_add_batch_to_shipment | Pass | 0.14 |
| test_db_constraints | test_tc10_same_batch_twice_rejected | Pass | 0.16 |
| test_db_constraints | test_incompatible_storage_ranges_rejected | Pass | 0.17 |
| test_db_constraints | test_status_and_timestamps_must_agree | Pass | 0.15 |
| test_db_constraints | test_tc16_overlapping_sensor_assignment_rejected | Pass | 0.18 |
| test_db_constraints | test_assignment_needs_exactly_one_target | Pass | 0.12 |
| test_db_constraints | test_tc28_app_role_cannot_delete_readings_or_audit | Pass | 0.12 |
| test_db_constraints | test_pincode_format | Pass | 0.06 |
| test_db_constraints | test_unique_email_case_insensitive | Pass | 0.17 |
| test_db_constraints | test_check_constraints_use_dates | Pass | 0.15 |
| test_db_monitoring | test_tc17_valid_reading_in_range_no_incident | Pass | 0.20 |
| test_db_monitoring | test_tc18_out_of_limit_reading_creates_incident | Pass | 0.20 |
| test_db_monitoring | test_tc24_only_breached_batches_are_linked | Pass | 0.16 |
| test_db_monitoring | test_tc19_repeated_breach_appends_and_escalates | Pass | 0.20 |
| test_db_monitoring | test_recovery_sets_end_time_and_new_breach_reopens_window | Pass | 0.17 |
| test_db_monitoring | test_tc20_duplicate_reading_rejected | Pass | 0.17 |
| test_db_monitoring | test_tc21_future_timestamp_stored_as_invalid_without_incident | Pass | 0.15 |
| test_db_monitoring | test_implausible_value_kept_but_invalid | Pass | 0.14 |
| test_db_monitoring | test_faulty_sensor_readings_are_suspicious | Pass | 0.11 |
| test_db_monitoring | test_tc22_gap_appears_in_quality_report | Pass | 0.15 |
| test_db_monitoring | test_tc23_original_reading_values_are_protected | Pass | 0.13 |
| test_db_monitoring | test_facility_excursion_uses_stock_at_that_time | Pass | 0.21 |
| test_db_monitoring | test_reading_from_unassigned_sensor_is_stored_only | Pass | 0.17 |
| test_db_transactions | test_tc11_dispatch_records_movements_checkpoint_and_status | Pass | 0.20 |
| test_db_transactions | test_tc12_partial_failure_rolls_back_everything | Pass | 0.18 |
| test_db_transactions | test_tc13_expired_batch_cannot_be_dispatched | Pass | 0.14 |
| test_db_transactions | test_tc13_quarantined_batch_cannot_be_dispatched | Pass | 0.16 |
| test_db_transactions | test_dispatch_requires_sensor | Pass | 0.14 |
| test_db_transactions | test_dispatch_blocked_for_faulty_vehicle | Pass | 0.14 |
| test_db_transactions | test_lines_frozen_after_dispatch | Pass | 0.14 |
| test_db_transactions | test_tc14_concurrent_dispatches_cannot_oversell | Pass | 0.75 |
| test_db_transactions | test_tc15_receive_moves_stock_and_closes_assignment | Pass | 0.17 |
| test_db_transactions | test_receive_requires_in_transit | Pass | 0.13 |
| test_db_workflow | test_tc26_operator_cannot_release_batch | Pass | 0.17 |
| test_db_workflow | test_status_change_needs_staff_context | Pass | 0.12 |
| test_db_workflow | test_investigator_may_hold_but_not_release | Pass | 0.14 |
| test_db_workflow | test_disposed_is_terminal | Pass | 0.15 |
| test_db_workflow | test_assigning_investigation_moves_incident_to_investigating | Pass | 0.15 |
| test_db_workflow | test_operator_cannot_be_assigned_investigation | Pass | 0.18 |
| test_db_workflow | test_tc29_complete_investigation_requires_findings | Pass | 0.15 |
| test_db_workflow | test_cannot_resolve_with_open_investigation | Pass | 0.18 |
| test_db_workflow | test_tc30_cannot_close_with_pending_action_or_unassessed_batch | Pass | 0.21 |
| test_db_workflow | test_tc31_close_fully_resolved_incident | Pass | 0.18 |
| test_db_workflow | test_incident_cannot_skip_states | Pass | 0.17 |
| test_db_workflow | test_tc32_dashboard_matches_base_tables | Pass | 0.18 |
| test_db_workflow | test_tc33_incident_report_totals_match | Pass | 0.17 |
| test_db_workflow | test_audit_log_never_stores_password_hash | Pass | 0.12 |
| test_db_workflow | test_related_shipments_same_vehicle | Pass | 0.17 |

## pytest output

```
....................................................................     [100%]
```
