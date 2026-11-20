# 8. Results and Snapshots

All screenshots come from the running system on its demonstration data, captured automatically with `tools/e2e/report_shots.mjs`.

## 8.1 Screens

![Login](screenshots/01_login.png){width=75%}

*Figure 8.1: Login page, with the demonstration accounts.*

![Dashboard](screenshots/02_dashboard.png){width=100%}

*Figure 8.2: Dashboard. Every counter is a live SQL view (`v_dashboard`).*

![Shipments](screenshots/03_shipments.png){width=100%}

*Figure 8.3: Shipment list, with status and overdue arrivals.*

![Shipment detail](screenshots/04_shipment_detail_SH002.png){width=100%}

*Figure 8.4: Shipment SH002: batches on board, the shared storage range, a timeline merging checkpoints, movements and the incident, the monitoring sensor, and the incident.*

![Planned shipment](screenshots/05_shipment_planned_SH006.png){width=100%}

*Figure 8.5: A planned shipment, ready to dispatch. Lines can be edited only in this state.*

![Batches](screenshots/06_batches.png){width=100%}

*Figure 8.6: Batch list. Quantities and expiry warnings are derived, not stored.*

![Batch trace](screenshots/07_batch_trace_B001.png){width=100%}

*Figure 8.7: Batch trace for B001: stock per facility, the chain of custody from movement history, shipments and incidents.*

![Products](screenshots/08_products.png){width=100%}

*Figure 8.8: Products, with their configured limits.*

![Monitoring](screenshots/12_monitoring_chart.png){width=100%}

*Figure 8.9: Monitoring: 24 hours of readings from TL-1001, with the limit lines and the reading table.*

![Incidents](screenshots/09_incidents.png){width=100%}

*Figure 8.10: Incident list.*

![Closed incident](screenshots/10_incident_closed_INC0001.png){width=100%}

*Figure 8.11: INC0001 (closed): readings, exposure, assessed batches, investigation, completed actions and audit history.*

![Incident under investigation](screenshots/11_incident_investigating_INC0002.png){width=100%}

*Figure 8.12: INC0002 (under investigation), with an overdue corrective action.*

![Report: incidents](screenshots/13a_report_incidents.png){width=100%}

*Figure 8.13: Report: incidents by type and severity.*

![Report: vehicles](screenshots/13c_report_vehicles.png){width=100%}

*Figure 8.14: Report: vehicles with repeated incidents (`HAVING COUNT(*) > 1`).*

![Report: pending actions](screenshots/13d_report_corrective.png){width=100%}

*Figure 8.15: Report: corrective actions pending completion.*

![Report: sensor quality](screenshots/13f_report_sensor.png){width=100%}

*Figure 8.16: Report: sensor data quality: gaps found with `LAG()`, plus invalid and suspicious readings.*

![Admin: facilities](screenshots/14a_admin_facilities.png){width=100%}

*Figure 8.17: Facilities, with multivalued phone numbers.*

![Admin: sensors](screenshots/14c_admin_sensors.png){width=100%}

*Figure 8.18: Sensors and where each one is attached.*

![Audit log](screenshots/14e_admin_audit.png){width=100%}

*Figure 8.19: Audit log: who changed what, when, from which value to which, and why.*

## 8.2 Demonstration scenario, step by step

![D01](screenshots/D01_dashboard_before_failure.png){width=100%}

*Figure 8.20: Step 1. The administrator selects in-transit shipment SH004 in the simulator panel.*

![D02](screenshots/D02_simulation_started.png){width=100%}

*Figure 8.21: Step 2. A refrigeration failure starts. A reading arrives every 2.5 s and rises above 8 °C.*

![D03](screenshots/D03_incidents_list_new_INC0003.png){width=100%}

*Figure 8.22: Step 3. INC0003 appears. Nobody created it: the database trigger raised it from the readings.*

![D04](screenshots/D04_incident_raised_automatically.png){width=100%}

*Figure 8.23: Step 4. The incident: readings against the 8 °C limit, exposure, a peak of 11.7 °C, and only the breached batches (B002, B006, B007).*

![D05](screenshots/D05_investigator_assigned.png){width=100%}

*Figure 8.24: Step 5. The quality manager assigns an investigator, and the incident moves to "investigating".*

![D06](screenshots/D06_investigation_recorded.png){width=100%}

*Figure 8.25: Step 6. The investigator assesses each batch, puts B002 on hold, adds a corrective action and completes the investigation with findings.*

![D07](screenshots/D07_close_refused_by_database.png){width=100%}

*Figure 8.26: Step 7. The quality manager tries to close the incident. The database refuses: "Incident 3 has corrective actions that are not finished".*

![D08](screenshots/D08_operator_completed_action.png){width=100%}

*Figure 8.27: Step 8. The operator marks the corrective action completed.*

![D09](screenshots/D09_incident_closed.png){width=100%}

*Figure 8.28: Step 9. The quality manager releases B002 and closes the incident. The history shows every step, with names and reasons.*

![D10](screenshots/D10_batch_trace_after_decisions.png){width=100%}

*Figure 8.29: Batch B002's trace: decisions on hold → released, with who made them and why.*

![D11](screenshots/D11_shipment_timeline_with_incident.png){width=100%}

*Figure 8.30: Shipment SH004's timeline now includes the incident.*

![D12](screenshots/D12_audit_log_after_demo.png){width=100%}

*Figure 8.31: The audit log after the scenario.*
