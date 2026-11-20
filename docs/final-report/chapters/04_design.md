# 4. System Design

## 4.1 Architecture

PharmaTrace has three tiers. It follows a "thin API over a smart database" principle: every integrity rule and workflow rule lives in PostgreSQL, as constraints, triggers, functions and views.

Each API request runs as **one transaction** under a least-privileged database role. The transaction's first statement records which staff member is acting, so the database triggers can enforce role rules and write the audit trail. The backend therefore cannot bypass the rules, and the rules can be demonstrated directly in SQL.

![Three-tier architecture](figures/arch_three_tier.png){width=100%}

*Figure 4.1: Three-tier architecture.*

## 4.2 Conceptual design: ER diagram (Chen notation)

The conceptual model has **14 entity sets**, one of them weak (SHIPMENT_CHECKPOINT), and **22 relationship sets**.

| Symbol | Meaning |
|---|---|
| Rectangle | Strong entity set |
| Double rectangle | Weak entity set (SHIPMENT_CHECKPOINT) |
| Diamond | Relationship set |
| Double diamond | Identifying relationship of a weak entity (HAS_CHECKPOINT) |
| Ellipse; underlined text | Attribute; key attribute |
| Ellipse, dashed underline | Partial key of the weak entity (checkpoint_no) |
| Double ellipse | Multivalued attribute (phone_number) |
| Dashed ellipse | Derived attribute (current_quantity, exposure_duration) |
| Ellipse with child ellipses | Composite attribute (address: street, city, pincode) |
| Single / double line | Partial / total participation |
| 1, N, M | Cardinality ratio |

![ER diagram in Chen notation](figures/er_diagram_chen.png){width=100%}

*Figure 4.2: PharmaTrace ER diagram (Chen notation).*

### Entity sets

| Entity | Key | Type | Description |
|---|---|---|---|
| PRODUCT | product_id | Strong | Medicine with configured storage limits |
| BATCH | batch_id | Strong | A manufactured lot of one product |
| FACILITY | facility_id | Strong | Warehouse, distribution centre, hospital, clinic or pharmacy |
| VEHICLE | vehicle_id | Strong | Refrigerated transport vehicle |
| SHIPMENT | shipment_id | Strong | One trip from an origin facility to a destination facility |
| SHIPMENT_CHECKPOINT | shipment_id + checkpoint_no | Weak | An event during a shipment; exists only with its shipment |
| BATCH_MOVEMENT | movement_id | Strong | One received, dispatched, returned or disposed movement of a batch |
| SENSOR | sensor_id | Strong | Temperature and/or humidity logger |
| SENSOR_ASSIGNMENT | assignment_id | Strong | A period during which a sensor monitors one shipment or one facility |
| SENSOR_READING | reading_id | Strong | One recorded measurement |
| INCIDENT | incident_id | Strong | A detected or reported cold-chain problem |
| INVESTIGATION | investigation_id | Strong | Investigation work on an incident |
| CORRECTIVE_ACTION | action_id | Strong | An action required by an investigation |
| STAFF | staff_id | Strong | A system user with a role |

### Relationship sets

| Relationship | Entities | Cardinality | Participation |
|---|---|---|---|
| HAS | PRODUCT – BATCH | 1 : N | BATCH total |
| CONTAINS (attribute: quantity_shipped) | SHIPMENT – BATCH | M : N | Both partial |
| CARRIES | VEHICLE – SHIPMENT | 1 : N | SHIPMENT total |
| ORIGINATES_FROM | FACILITY – SHIPMENT | 1 : N | SHIPMENT total |
| DESTINED_TO | FACILITY – SHIPMENT | 1 : N | SHIPMENT total |
| HAS_CHECKPOINT (identifying) | SHIPMENT – SHIPMENT_CHECKPOINT | 1 : N | SHIPMENT_CHECKPOINT total |
| MOVES | BATCH – BATCH_MOVEMENT | 1 : N | BATCH_MOVEMENT total |
| RECORDED_AT | FACILITY – BATCH_MOVEMENT | 1 : N | BATCH_MOVEMENT total |
| VIA | SHIPMENT – BATCH_MOVEMENT | 1 : N | Both partial (an initial intake has no shipment) |
| DEPLOYED_AS | SENSOR – SENSOR_ASSIGNMENT | 1 : N | SENSOR_ASSIGNMENT total |
| ATTACHED_TO | SHIPMENT – SENSOR_ASSIGNMENT | 1 : N | Both partial |
| INSTALLED_AT | FACILITY – SENSOR_ASSIGNMENT | 1 : N | Both partial |
| GENERATES | SENSOR – SENSOR_READING | 1 : N | SENSOR_READING total |
| EVIDENCED_BY (attribute: relevance_note) | INCIDENT – SENSOR_READING | M : N | Both partial |
| AFFECTS (attributes: assessment_status, assessment_note) | INCIDENT – BATCH | M : N | Both partial |
| CONCERNS | SHIPMENT – INCIDENT | 1 : N | Both partial |
| OCCURS_AT | FACILITY – INCIDENT | 1 : N | Both partial |
| REPORTS | STAFF – INCIDENT | 1 : N | Both partial (only manual incidents have a reporter) |
| INVESTIGATED_IN | INCIDENT – INVESTIGATION | 1 : N | INVESTIGATION total |
| ASSIGNED_TO | STAFF – INVESTIGATION | 1 : N | INVESTIGATION total |
| REQUIRES | INVESTIGATION – CORRECTIVE_ACTION | 1 : N | CORRECTIVE_ACTION total |
| RESPONSIBLE_FOR | STAFF – CORRECTIVE_ACTION | 1 : N | CORRECTIVE_ACTION total |

Some constraints cannot be drawn in Chen notation and are enforced in the database instead:

- a sensor assignment and an incident each refer to exactly one of SHIPMENT or FACILITY (an exclusive or);
- a sensor's assignment periods must not overlap;
- derived attributes are computed by views.

## 4.3 Logical design: normalisation to 3NF

Notation: **bold** marks a primary key, *italic* a foreign key, and X → Y means X functionally determines Y.

### Unnormalised form

The data begins as one record per shipment, as an operator might keep it in a spreadsheet. Groups in braces repeat inside a record:

> CHAIN_RECORD (ShipmentID, DispatchTime, ShipmentStatus, VehicleRegNo, VehicleType, OriginName, OriginCity, DestName, DestCity, {DestPhone}, {BatchNo, ProductName, ProductType, MinTemp, MaxTemp, ExpiryDate, QtyShipped}, {SensorSerial, SensorType, RecordedAt, Temperature}, IncidentID, IncidentType, Severity, {InvestigatorEmail, InvestigatorName, Findings})

This form has five problems:

- **Values are not atomic.** Phones, batches and readings are lists inside one cell.
- **Data is redundant.** Vehicle and product details repeat in every shipment record. A shipment with 10,000 readings would repeat them 10,000 times if flattened.
- **Insertion anomaly.** A product cannot be recorded until it has been shipped.
- **Update anomaly.** Changing Vaccine A's limits means editing every record that contains it.
- **Deletion anomaly.** Deleting a shipment can lose the only record of a batch.

### First normal form

Each repeating group moves to its own relation, together with the parent's key. The 1NF relations are:

- SHIPMENT_INFO (**ShipmentID**, …)
- FACILITY_PHONE (**FacilityName, PhoneNumber**)
- SHIPMENT_BATCH_INFO (**ShipmentID, BatchNo**, ProductName, ProductType, MinTemp, MaxTemp, ExpiryDate, QtyShipped)
- READING_INFO (**SensorSerial, RecordedAt**, SensorType, Temperature, ShipmentID)
- INCIDENT_INFO (**IncidentID**, …)
- INVESTIGATION_INFO (**IncidentID, InvestigatorEmail**, InvestigatorName, Findings)

### Second normal form: remove partial dependencies

| Relation | Partial dependency | Decomposition |
|---|---|---|
| SHIPMENT_BATCH_INFO | BatchNo → ProductName, ProductType, MinTemp, MaxTemp, ExpiryDate | BATCH_INFO (**BatchNo**, …) + SHIPMENT_BATCH (**ShipmentID, BatchNo**, QtyShipped) |
| READING_INFO | SensorSerial → SensorType | SENSOR (**SensorSerial**, SensorType) + READING (**SensorSerial, RecordedAt**, Temperature) |
| INVESTIGATION_INFO | InvestigatorEmail → InvestigatorName | STAFF (**Email**, StaffName) + INVESTIGATION (**IncidentID, InvestigatorEmail**, Findings) |

ShipmentID in READING_INFO does not depend on an individual reading. It depends on which shipment the sensor was attached to during a period, so it moves to SENSOR_ASSIGNMENT (sensor, shipment, assigned_at, unassigned_at), where it is stored once per assignment instead of once per reading.

### Third normal form: remove transitive dependencies

| Relation | Transitive dependency | Decomposition |
|---|---|---|
| SHIPMENT_INFO | ShipmentID → VehicleRegNo → VehicleType | VEHICLE (**VehicleRegNo**, VehicleType) |
| SHIPMENT_INFO | ShipmentID → OriginName → OriginCity (likewise for the destination) | FACILITY (**FacilityName**, FacilityType, Street, City, Pincode) |
| BATCH_INFO | BatchNo → ProductName → ProductType, MinTemp, MaxTemp | PRODUCT (**ProductName**, ProductType, MinTemp, MaxTemp) |

**Surrogate keys.** Natural keys (product_name, batch_number, registration_number, serial_number, email) are kept as UNIQUE candidate keys, and integer surrogate keys are added for stable joins. This does not change any functional dependency.

**Derived values are never stored.** Current quantity, current location, exposure duration and expiry state are computed by views. Storing them would reintroduce update anomalies.

### Final schema (18 relations, plus 2 supporting tables)

| # | Table | Attributes | Candidate keys | Functional dependencies |
|---|---|---|---|---|
| 1 | PRODUCT | **product_id**, product_name, product_type, min_temp, max_temp, min_humidity, max_humidity | product_id; product_name | product_id → all |
| 2 | BATCH | **batch_id**, batch_number, *product_id*, manufacturing_date, expiry_date, initial_quantity, batch_status | batch_id; batch_number | batch_id → all |
| 3 | FACILITY | **facility_id**, facility_name, facility_type, street, city, pincode | facility_id; facility_name | facility_id → all |
| 4 | FACILITY_PHONE | ***facility_id*, phone_number** | (facility_id, phone_number) | All-key |
| 5 | VEHICLE | **vehicle_id**, registration_number, vehicle_type, refrigeration_status | vehicle_id; registration_number | vehicle_id → all |
| 6 | SHIPMENT | **shipment_id**, *vehicle_id*, *origin_facility_id*, *destination_facility_id*, dispatch_time, expected_arrival, actual_arrival, shipment_status | shipment_id | shipment_id → all |
| 7 | SHIPMENT_BATCH | ***shipment_id*, *batch_id***, quantity_shipped | (shipment_id, batch_id) | key → quantity_shipped |
| 8 | SHIPMENT_CHECKPOINT | ***shipment_id*, checkpoint_no**, checkpoint_time, event_type, location_description | (shipment_id, checkpoint_no) | key → all |
| 9 | BATCH_MOVEMENT | **movement_id**, *batch_id*, *facility_id*, *shipment_id*, movement_type, movement_time, quantity_moved | movement_id | movement_id → all |
| 10 | SENSOR | **sensor_id**, serial_number, sensor_type, installation_status, expected_interval_s | sensor_id; serial_number | sensor_id → all |
| 11 | SENSOR_ASSIGNMENT | **assignment_id**, *sensor_id*, *shipment_id*, *facility_id*, assigned_at, unassigned_at | assignment_id | assignment_id → all |
| 12 | SENSOR_READING | **reading_id**, *sensor_id*, recorded_at, ingested_at, temperature, humidity, quality_status | reading_id; (sensor_id, recorded_at) | both keys → all |
| 13 | STAFF | **staff_id**, staff_name, email, password_hash, role, account_status | staff_id; email | staff_id → all |
| 14 | INCIDENT | **incident_id**, incident_type, severity, detection_source, *shipment_id*, *facility_id*, *reported_by*, detected_at, start_time, end_time, incident_status, description | incident_id | incident_id → all |
| 15 | INCIDENT_READING | ***incident_id*, *reading_id***, relevance_note | (incident_id, reading_id) | key → relevance_note |
| 16 | INCIDENT_BATCH | ***incident_id*, *batch_id***, assessment_status, assessment_note | (incident_id, batch_id) | key → assessment attributes |
| 17 | INVESTIGATION | **investigation_id**, *incident_id*, *assigned_to*, started_at, completed_at, findings, investigation_status | investigation_id | investigation_id → all |
| 18 | CORRECTIVE_ACTION | **action_id**, *investigation_id*, *assigned_to*, action_description, due_date, completed_at, action_status | action_id | action_id → all |

The two supporting tables are BATCH_STATUS_TRANSITION (**from_status, to_status, role**: an all-key table holding the workflow rules) and AUDIT_LOG (**audit_id**, table_name, row_pk, action, old_data, new_data, *changed_by*, reason, changed_at).

**3NF/BCNF check.** In every table, the only determinants are candidate keys, so no partial or transitive dependency remains. The schema is in 3NF, and also in BCNF. Pincode is deliberately not treated as determining city, because one PIN code can cover several localities.

## 4.4 Data flow diagrams (Yourdon–DeMarco notation)

Each level is balanced with its parent: every data flow that enters or leaves a parent process appears again on its child diagram.

![DFD Level 0](figures/dfd_level0.png){width=80%}

*Figure 4.3: DFD Level 0 (context diagram), with five external entities.*

![DFD Level 1](figures/dfd_level1.png){width=100%}

*Figure 4.4: DFD Level 1: seven processes and nine data stores.*

| Process | Name | Description |
|---|---|---|
| 1.0 | Manage Staff and Access | Create staff accounts and roles |
| 2.0 | Manage Products, Batches and Facilities | Master data and batch intake |
| 3.0 | Manage Shipments | Create, load, assign a sensor, dispatch and receive (as transactions) |
| 4.0 | Monitor Sensor Readings | Ingest, reject duplicates, classify and store readings |
| 5.0 | Detect and Trace Incidents | Compare readings with limits; raise or update incidents; link readings and batches |
| 6.0 | Investigate and Resolve | Assign investigators, record findings, decisions and actions, close incidents |
| 7.0 | Generate Reports and Dashboard | Dashboard counters and reports |

| Store | Tables |
|---|---|
| D1 Staff | STAFF |
| D2 Product & Batch | PRODUCT, BATCH |
| D3 Facility & Vehicle | FACILITY, FACILITY_PHONE, VEHICLE |
| D4 Shipment & Movement | SHIPMENT, SHIPMENT_BATCH, SHIPMENT_CHECKPOINT, BATCH_MOVEMENT |
| D5 Sensor & Assignment | SENSOR, SENSOR_ASSIGNMENT |
| D6 Sensor Reading | SENSOR_READING |
| D7 Incident | INCIDENT, INCIDENT_READING, INCIDENT_BATCH |
| D8 Investigation & Action | INVESTIGATION, CORRECTIVE_ACTION |
| D9 Audit Log | AUDIT_LOG |

![DFD Level 2, process 5.0](figures/dfd_level2_p5.png){width=100%}

*Figure 4.5: DFD Level 2 for process 5.0, Detect and Trace Incidents.*

| Process | Name | Description |
|---|---|---|
| 5.1 | Determine Monitored Target | The shipment or facility the sensor was assigned to at the reading's time |
| 5.2 | Identify Batches at Target | The shipment's batches, or stock at the facility at that time |
| 5.3 | Check Product Limits | Compare the reading with each batch's product limits |
| 5.4 | Create or Update Incident | Open a new incident or add to the active one; record the end time when readings recover |
| 5.5 | Link Readings and Batches | Link the breaching readings and the breached batches |
| 5.6 | Record Manual Incident | Store an incident reported by staff |

![DFD Level 2, process 6.0](figures/dfd_level2_p6.png){width=100%}

*Figure 4.6: DFD Level 2 for process 6.0, Investigate and Resolve.*

| Process | Name | Description |
|---|---|---|
| 6.1 | Assign Investigator | Quality manager assigns; investigator receives the incident details |
| 6.2 | Record Findings and Assessments | Findings and per-batch assessments; may request a hold |
| 6.3 | Record Batch Decision | Hold, quarantine, release, return or dispose, with an audit entry |
| 6.4 | Manage Corrective Actions | Actions with a responsible person and due date |
| 6.5 | Close Incident | Check that everything is complete; close; audit entry |

## 4.5 Workflow design

![Incident lifecycle](figures/workflow_incident_lifecycle.png){width=100%}

*Figure 4.7: Incident lifecycle, enforced by the trigger `trg_incident_lifecycle`.*

![Batch decision workflow](figures/workflow_batch_status.png){width=100%}

*Figure 4.8: Batch status transitions per role, stored as rows of BATCH_STATUS_TRANSITION and enforced by `trg_batch_status_check`.*
