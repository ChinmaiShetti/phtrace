---
title: "PharmaTrace: Pharmaceutical Cold-Chain Integrity, Traceability and Incident Management System"
subtitle: "DBMS Mini Project — Final Report"
author:
  - "Chinmai Kiran Shetti (USN 1RV24CS068)"
  - "Department of Computer Science and Engineering, RV College of Engineering, Bengaluru"
  - "Database Management Systems Laboratory (CD2521A)"
date: "November 2026"
lang: en-GB
---

# Abstract {.unnumbered}

Temperature-sensitive medicines such as vaccines, insulin and biologics must stay within configured temperature limits from the warehouse to the hospital. When a refrigeration unit fails during storage or transport, an organisation must quickly answer:

- which shipment or facility was affected;
- which batches were inside, and whose limits were actually breached;
- how long they were exposed, and where they went next;
- who investigated, what was decided, and which corrective actions were completed.

PharmaTrace answers these questions from one normalised relational database.

The system was implemented as a three-tier web application:

| Tier | Implementation |
|---|---|
| Database | PostgreSQL 18: 20 tables in third normal form, 27 foreign keys, 50 CHECK constraints and 1 EXCLUDE constraint, 24 functions, 18 triggers, 14 views |
| Backend | Python FastAPI (50 endpoints) |
| Frontend | React with TypeScript (12 pages) |

The integrity rules and the workflow are enforced by the database itself:

- a temperature excursion raises an incident automatically, linking only the batches whose own product limits were breached;
- dispatching a shipment is a single atomic, concurrency-safe transaction;
- batch decisions follow role-based transition rules;
- an incident can be closed only by a quality manager, after every investigation, corrective action and batch assessment is complete;
- every decision is written to an audit log.

All 34 planned test cases pass. The evidence was produced by running each case against a fresh database and recording the system's actual response. The full suite of 68 automated tests also passes, and the complete scenario was driven end to end through the web interface.

For the Innovative Experiment, a B+ tree and a learned index (ALEX) were benchmarked on 8.64 million sensor-reading keys under six workload phases modelled on the cold-chain scenario. A proposed variant, ALEX-HB, was then implemented and measured. It absorbs insert hot spots in a small B+ tree buffer and migrates them later.

| Measurement | Result |
|---|---|
| Lookups, ALEX vs B+ tree | About 2× faster |
| Worst insert pause during insert bursts, ALEX | Up to 37.5 ms |
| Worst insert pause, ALEX-HB | Below 0.11 ms |
| Throughput in the combined-shift phase, ALEX-HB vs plain ALEX | 2.4× higher |
| Cost of ALEX-HB | Halved throughput in the investigation phase, where its deferred migration runs |

**Keywords:** relational database, normalisation, transactions, triggers, cold chain, traceability, learned index, ALEX.


# 1. Introduction

## 1.1 Background

A pharmaceutical cold chain is the sequence of storage and transport steps that keeps temperature-sensitive products within their configured limits. A typical route runs:

1. from a central warehouse,
2. by refrigerated vehicle,
3. to a regional distribution centre,
4. and on to hospitals, clinics and pharmacies.

Data loggers (sensors) record the temperature, and sometimes the humidity, at each stage.

Monitoring by itself is not enough. When a logger reports a reading outside the limits, that reading must be connected to:

- the shipment or facility where it happened;
- the batches present at that moment;
- the later movements of those batches;
- the people who decide what happens next.

When shipment records, sensor logs and investigation notes are kept separately, this link is slow to establish and easy to get wrong.

## 1.2 Problem Statement

When a temperature excursion occurs, the organisation must answer quickly and reliably:

1. Which shipment or facility experienced the problem, and when?
2. Which batches were present, in what quantity, and whose own product limits were breached?
3. How long were they exposed, and what was the peak temperature?
4. Which other shipments might have been affected (same vehicle, same facility, same period)?
5. Where have the affected batches since been delivered?
6. Who investigated, what was found, what decision was recorded for each batch, and which corrective actions were completed?

PharmaTrace stores all of this in one normalised relational database, where the integrity rules and the workflow are enforced by the database itself.

## 1.3 Motivation

The scenario exercises the core topics of a database course:

- an ER model with a weak entity, many-to-many relationships, composite, multivalued and derived attributes;
- normalisation to third normal form;
- integrity constraints;
- multi-step transactions under concurrency;
- role-based security;
- auditing;
- reporting queries.

It also generates a realistic data-management workload: millions of time-stamped sensor readings, with sudden bursts of inserts and queries during an incident. This workload motivates the indexing experiment in Chapter 9.

PharmaTrace supports traceability and investigation. **It does not decide whether a medicine is safe to use.** That decision is recorded by authorised quality staff, following their organisation's procedures.

## 1.4 Objectives

| # | Objective | Status |
|---|---|---|
| O1 | Design a normalised (3NF) relational schema for cold-chain data | Achieved (Chapter 4) |
| O2 | Record batch movements as history, so the chain of custody can be reconstructed | Achieved |
| O3 | Store sensor readings without altering originals, and detect readings outside product limits | Achieved |
| O4 | Raise incidents automatically and link the relevant readings and the breached batches | Achieved |
| O5 | Support a role-controlled investigation and corrective-action workflow through to closure | Achieved |
| O6 | Enforce integrity with keys, constraints, triggers and transactions | Achieved (Chapter 5) |
| O7 | Provide forms, a dashboard and SQL-based reports, with security and validation | Achieved (Chapters 5, 6, 8) |
| O8 | Evaluate a learned index against a B+ tree on cold-chain workloads, and test an improvement | Achieved (Chapter 9) |

## 1.5 Scope

**In scope:**

- products, batches, facilities and vehicles;
- shipments with checkpoints;
- simulated sensor readings and excursion detection;
- incidents, investigations, batch decisions and corrective actions;
- role-based access, the audit trail, the dashboard and reports;
- an index benchmark.

**Out of scope:**

- physical IoT hardware (readings are simulated by software);
- GPS tracking;
- any automatic decision on whether a medicine is usable;
- integrating the learned index into PostgreSQL (the benchmark runs on its own).

The temperature limits and severity thresholds used are illustrative configured values, not real product specifications.

## 1.6 Organisation of the Report

| Chapter | Contents |
|---|---|
| 2 | Related work |
| 3 | Requirements |
| 4 | Design: the architecture, ER model, normalisation and data-flow diagrams |
| 5 | Implementation of the database, backend and frontend |
| 6 | Forms, security and validation |
| 7 | Testing, with the evidence for every test case |
| 8 | Screenshots of the working system, and the demonstration scenario |
| 9 | The Innovative Experiment |
| 10 | Conclusion |

The appendices contain the installation guide, the API reference, the full test evidence, key SQL listings and the demonstration script.


# 2. Literature Survey

Prior work covers three areas: cold-chain guidance and monitoring systems, relational database design, and learned indexes. Cold-chain monitoring is a well-established field, so PharmaTrace does not claim novelty there. Its contribution is a well-defined workflow, enforced by the database, from an excursion to a closed and audited investigation.

## 2.1 Cold-chain guidance and monitoring systems

- **WHO guidance.** The World Health Organization's *Model guidance for the storage and transport of time- and temperature-sensitive pharmaceutical products* [1] sets out storage and distribution requirements. Its technical supplements [2] cover temperature mapping, monitoring of storage areas and transport operations, and temperature-controlled road transport. PharmaTrace follows this split by monitoring both fixed facilities and shipments in transit.
- **IoT risk monitoring.** Tsang et al. [3] combined a wireless sensor network, a cloud database and fuzzy logic to monitor product-quality and occupational-safety risk in cold chains.
- **Early warning.** Liu [4] proposed a big-data risk-assessment and early-warning architecture for pharmaceutical cold-chain transport. It combines rule-based thresholds with machine-learning risk scoring.
- **Digital twin.** Wu et al. [5] built an Internet-of-Everything and digital-twin platform with temperature and humidity monitoring and anomaly warnings, deployed in a pharmaceutical distribution centre.

| Work | Monitoring and alerts | Batch-level traceability | Investigation and corrective-action records | Integrity enforced in the database |
|---|---|---|---|---|
| Tsang et al. [3] | Yes | Not a focus | No | Not a focus |
| Liu [4] | Yes, with risk scoring | Not a focus | Warning response only | Not a focus |
| Wu et al. [5] | Yes | Shipment records | No | Not a focus |
| **PharmaTrace** | Yes, rule-based | Yes, from movement history | Yes, with role rules and an audit trail | Yes: constraints, triggers, transactions |

This comparison is based on the published descriptions of these works. The gap PharmaTrace addresses is the link those systems leave to separate processes: from an alert, to the exact batches affected, their chain of custody, and a documented, role-controlled resolution.

## 2.2 Database design foundations

The design follows standard ER modelling and normalisation theory [10], [11]:

- Chen notation for the conceptual model;
- ER-to-relational mapping, including weak entities and many-to-many relationships;
- functional-dependency analysis up to third normal form.

The implementation relies on PostgreSQL features [12]:

- CHECK constraints, and EXCLUDE constraints with GiST indexes;
- PL/pgSQL functions and triggers;
- row-level locking with `SELECT … FOR UPDATE`;
- role privileges;
- `SECURITY DEFINER` functions.

The B+ tree [13], [14] is the default index structure in relational database systems, including PostgreSQL, and is the baseline in Chapter 9.

## 2.3 Learned indexes

- **The idea.** Kraska et al. [6] proposed treating an index as a model that maps a key to its position. They showed that learned models can outperform B-trees on read-only data.
- **ALEX.** ALEX [7] extended learned indexes to updatable workloads, using gapped arrays, adaptive node expansion and node splitting. Its authors report up to 4.1× higher throughput than a B+ tree across read-write workloads.
- **Independent evaluations.** Benchmarks by other researchers [8], [9] confirm large gains on read-heavy, in-memory workloads. They also note that insert behaviour, bulk loading and concurrency vary widely between designs.

These evaluations mostly use static datasets or stationary operation mixes. Chapter 9 asks a different question: how does a learned index behave when the insert and query distribution shifts suddenly, as it does during a cold-chain incident? It then measures one way of reducing the cost of such shifts.

Update buffers placed in front of learned indexes appear in earlier designs (for example XIndex and FINEdex). The variant tested here therefore makes no claim that buffering itself is new.


# 3. Requirement Specification

## 3.1 Users and roles

| Role | Responsibilities |
|---|---|
| Operator | Registers products, batches, facilities, vehicles and sensors; creates, dispatches and receives shipments; records checkpoints; reports manual incidents; completes corrective actions assigned to them |
| Investigator | Records investigation findings; assesses affected batches; places batches on hold; adds corrective actions |
| Quality manager | Assigns investigators; quarantines, releases, returns or disposes of batches; resolves and closes incidents; reads the audit log |
| Administrator | Manages staff accounts and roles; runs the reading simulator; reads the audit log |

## 3.2 Functional requirements

| ID | Requirement | Implemented by |
|---|---|---|
| FR-01 | Authenticate staff by email and password, and restrict every action by role | `/api/auth/login`, JWT, `require()` checks, database triggers |
| FR-02 | Register products with configured minimum and maximum storage temperature (and optional humidity) limits | `product` table and form |
| FR-03 | Register batches with a unique batch number, manufacturing date, expiry date and initial quantity | `batch` table; intake movement recorded in the same transaction |
| FR-04 | Maintain facilities (warehouse, distribution centre, hospital, clinic, pharmacy) and refrigerated vehicles | `facility`, `facility_phone`, `vehicle` |
| FR-05 | Create a shipment with vehicle, origin, destination and expected arrival, and attach batches with quantities | `shipment`, `shipment_batch` |
| FR-06 | Dispatch a shipment in one transaction: verify stock and batch status, record dispatch movements and a departure checkpoint, set status in transit | `dispatch_shipment()` |
| FR-07 | Receive a shipment in one transaction: record received movements and an arrival checkpoint, set status delivered | `receive_shipment()` |
| FR-08 | Record every batch movement as history, and derive current stock per facility from it | `batch_movement`, `v_batch_stock` |
| FR-09 | Assign sensors to a shipment or facility for a period, and prevent overlapping assignments of one sensor | `sensor_assignment` with an EXCLUDE constraint |
| FR-10 | Store each reading with timestamp and quality status, and never overwrite original values | `sensor_reading`, `trg_reading_protect` |
| FR-11 | Compare each valid reading with the limits of the products present, and raise or update an incident on a breach | `trg_reading_evaluate`, `record_excursion()` |
| FR-12 | Link an incident to its shipment or facility, the relevant readings and the potentially affected batches | `incident_reading`, `incident_batch` |
| FR-13 | Let a quality manager assign an investigator, and the investigator record findings | `investigation` |
| FR-14 | Record batch decisions (hold, quarantine, release, return, dispose), with user, time and reason | `batch_status_transition`, `audit_log` |
| FR-15 | Record corrective actions with a responsible person, due date and status | `corrective_action` |
| FR-16 | Close an incident only when every investigation and corrective action is complete and every affected batch is assessed | `trg_incident_lifecycle` |
| FR-17 | Trace a batch: product, shipments, facilities, readings, incidents and current status | `/api/batches/{id}/trace`, Batch Trace page |
| FR-18 | Show a dashboard: active shipments, open incidents, batches under investigation, overdue actions, recent excursions, overdue arrivals | `v_dashboard` |
| FR-19 | Generate reports: incidents by type and severity, batches in incidents, repeated incidents per vehicle, pending actions, expiring batches, sensor data quality | Six `v_report_*` views |

## 3.3 Non-functional requirements

| ID | Category | Requirement | How it is met |
|---|---|---|---|
| NFR-01 | Integrity | All relationships enforced by keys and constraints | 20 primary keys, 27 foreign keys, 50 CHECK constraints, 1 EXCLUDE constraint, UNIQUE keys |
| NFR-02 | Consistency | Multi-step operations are atomic | PL/pgSQL functions; one transaction per API request |
| NFR-03 | Concurrency | Concurrent dispatches never make stock negative | Row locks taken in batch_id order (TC14) |
| NFR-04 | Security | Hashed passwords; role-based access; parameterised SQL; least-privilege database role | Argon2, JWT, `require()`, database triggers, `pharmatrace_app` grants |
| NFR-05 | Auditability | Status changes logged with user, time, old and new values and reason | Generic `trg_audit` trigger (SECURITY DEFINER) |
| NFR-06 | Performance | Dashboard and incident pages load within 2 s on the demonstration data set | Views with indexes; measured interactively |
| NFR-07 | Usability | Web forms with field-level validation messages; works in a modern browser | Mantine forms (Chapter 6) |
| NFR-08 | Maintainability | Schema kept as version-controlled SQL scripts; database rebuildable from them | `db/*.sql`, `reset_db.py` |

## 3.4 Business rules enforced in the database

1. A batch's expiry date must be after its manufacturing date, and quantities must be positive.
2. A shipment's origin and destination must differ. The shipment's status must agree with its dispatch and arrival times.
3. An expired, quarantined, on-hold or disposed batch cannot be dispatched. Stock at the origin must cover the requested quantity.
4. All products on one shipment must have overlapping temperature ranges.
5. A sensor assignment targets exactly one shipment or one facility. A sensor's assignment periods cannot overlap.
6. Only one active incident is allowed per shipment (or facility) per incident type. Repeated breaches are appended to it.
7. A reading with the same sensor and timestamp as an existing reading is a duplicate and is rejected. A reading's original values can never be changed or deleted.
8. Batch status changes must follow the transitions allowed for the acting staff member's role.
9. An incident moves open → investigating → resolved → closed. It may be reopened from resolved to investigating. Closing requires a quality manager, no pending corrective actions, and every affected batch assessed.

## 3.5 Hardware and software

| Type | Used / required |
|---|---|
| Processor | Any x86-64 (developed on AMD Ryzen 5 7535HS) |
| Memory | 8 GB recommended |
| Operating system | Windows 10/11 (developed on Windows 11); also runs on Linux and macOS |
| Database | PostgreSQL 18 (18.3) with the btree_gist extension |
| Backend | Python 3.12, FastAPI, psycopg 3, Pydantic 2, PyJWT, pwdlib (Argon2); managed with uv |
| Frontend | Node.js 22, React 19, TypeScript, Vite, Mantine 8, TanStack Query 5, React Router 7, Recharts |
| Testing | pytest, ruff; Playwright (driving Microsoft Edge) for browser checks |
| Benchmark | Docker (gcc:14 image, CMake), C++17, tlx, ALEX; Python with numpy and matplotlib |
| Browser | Current Chrome, Edge or Firefox |

## 3.6 Assumptions and constraints

- Sensor readings are simulated: every 5 minutes for normal operation, and every 2.5 seconds during the live failure demonstration.
- Temperature limits and severity thresholds are illustrative, configured values.
- The software records decisions; it does not decide whether a medicine is usable.
- All timestamps are stored as `timestamptz` (UTC) and shown in the browser's local time.


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


# 5. Implementation

## 5.1 Technology stack and project structure

| Layer | Technology | Location |
|---|---|---|
| Database | PostgreSQL 18; SQL and PL/pgSQL scripts applied in order | `db/00_extensions.sql` … `db/06_grants.sql` |
| Backend | Python 3.12, FastAPI, psycopg 3 (connection pool), Pydantic 2, PyJWT, pwdlib (Argon2) | `backend/app/` |
| Frontend | React 19, TypeScript, Vite, Mantine 8, TanStack Query 5, React Router 7, Recharts | `frontend/src/` |
| Tooling | uv, ruff, pytest; Playwright with Microsoft Edge; Docker | `backend/tests/`, `tools/e2e/` |
| Launchers | `run.bat` (set up and start), `stop.bat` (stop) | repository root |

![Project size](figures/project_size.png){width=100%}

*Figure 5.1: Database and API objects, and lines of code by part of the project.*

`backend/scripts/reset_db.py` builds the whole database from the SQL scripts:

1. It creates two roles: `pharmatrace_owner`, which owns the schema, and `pharmatrace_app`, which the API uses.
2. It drops and recreates the database.
3. It creates the `btree_gist` extension.
4. It applies `db/*.sql` in order.
5. It loads deterministic demonstration data. The data's timestamps are relative to the time the script is run.

## 5.2 Database implementation

### Tables and constraints (`01_tables.sql`)

There are 20 tables. Every primary key is an identity column, apart from the composite keys of the junction tables and of the weak entity. Foreign keys use `ON DELETE RESTRICT`, except where a child row has no meaning without its parent (phone numbers, shipment lines, checkpoints, incident links), which use `ON DELETE CASCADE`.

| Constraint (name) | Rule |
|---|---|
| `product_temp_range`, `product_humidity_pair`, `product_humidity_range` | min < max; humidity limits given both-or-neither, within 0–100 |
| `batch_dates`, quantity CHECK, `batch_status` CHECK | Expiry after manufacture; quantity > 0; status from a fixed list |
| `shipment_route` | Origin ≠ destination |
| `shipment_status_times` | Planned ⇒ no dispatch or arrival time; in transit ⇒ dispatched, not arrived; delivered ⇒ both |
| `shipment_arrival_after_dispatch` | actual_arrival ≥ dispatch_time |
| `movement_dispatch_needs_shipment` | A dispatch movement must name its shipment |
| `assignment_one_target`, `incident_one_target` | Exactly one of shipment or facility (`num_nonnulls(...) = 1`) |
| `assignment_no_overlap` | `EXCLUDE USING gist (sensor_id WITH =, tstzrange(assigned_at, unassigned_at) WITH &&)` |
| `reading_unique_per_sensor`, `reading_has_value` | No duplicate (sensor, time); at least one measured value |
| `incident_manual_reporter`, `incident_period` | Manual incidents need a reporter; end ≥ start |
| `incident_active_shipment_uq`, `incident_active_facility_uq` | Partial unique indexes: one active incident per target and type |
| `assessed_needs_note` | An assessed batch needs a note |
| `investigation_completion`, `investigation_findings` | Completed ⇔ completed_at set; completed needs findings |
| `action_completion` | Completed ⇔ completed_at set |
| `staff_email_uq` | Unique `lower(email)` |
| pincode, phone, registration formats | Regular-expression CHECKs |

### Indexes (`02_indexes.sql`)

There are 24 explicit indexes in this file, plus the 3 unique indexes created in `01_tables.sql`:

- B-tree indexes on every foreign key used in joins;
- partial indexes serving the dashboard (shipments in transit, active incidents, open corrective actions);
- a **BRIN** index on `sensor_reading(recorded_at)`, which is small and suits the append-only time series.

Per-sensor lookups use the `UNIQUE (sensor_id, recorded_at)` B-tree.

### Functions and transactions (`03_functions.sql`)

| Function | Purpose |
|---|---|
| `current_staff_id()`, `current_staff_role()` | Read the acting user from the transaction setting `app.current_staff_id` |
| `batch_stock_at(batch, facility, time)` | Stock derived from the movement history |
| `batches_at_target(shipment, facility, time)` | Batches present at a monitored place and time |
| **`dispatch_shipment(id, time)`** | Atomic dispatch (described below) |
| **`receive_shipment(id, time)`** | Atomic receipt: received movements, arrival checkpoint, sensor assignments ended, status delivered |
| `shipment_timeline(id)` | Checkpoints, movements and incidents merged in time order (`UNION ALL`) |
| `related_shipments(incident)` | Other shipments on the same vehicle or at the same facility during the incident window |
| `severity_rank`, `severity_for_deviation`, `movement_sign` | Helper functions |

`dispatch_shipment` runs as one transaction:

1. It locks the shipment row.
2. It checks the status (planned), that at least one batch is on board, that an active sensor is attached, and that the vehicle's refrigeration is not faulty.
3. It locks the batch rows **in batch_id order**.
4. For each line, it checks the batch status, expiry and stock at the origin.
5. It inserts the dispatch movements and a departure checkpoint, and sets the shipment in transit.

Any failure raises an exception that undoes every step. The fixed locking order means two concurrent dispatches of the same stock cannot deadlock. The second waits for the first, then fails on stock (TC14). The full listing is in Appendix D.

### Triggers (`04_triggers.sql`)

| Trigger | Table and timing | Purpose |
|---|---|---|
| `shipment_batch_check` | shipment_batch, before insert/update/delete | Lines change only while the shipment is planned; product temperature ranges must overlap |
| `sensor_assignment_check` | sensor_assignment, before insert/update | Only active sensors; not on delivered or cancelled shipments |
| `reading_classify` | sensor_reading, before insert | Marks implausible values (outside −80…80 °C or 0…100 % RH) or future timestamps as invalid, and readings from faulty sensors as suspicious; the raw value is always kept |
| `reading_protect` | sensor_reading, before update/delete | Original values can never change; only `quality_status` may |
| `reading_evaluate` | sensor_reading, after insert | **Excursion detection** (described below) |
| `batch_status_check` | batch, before update of batch_status | The transition must be listed in BATCH_STATUS_TRANSITION for the acting user's role |
| `incident_lifecycle` | incident, before update of incident_status | Allowed state moves; the rules for resolving and closing |
| `investigation_check`, `investigation_opened` | investigation | Assignee must be an active investigator or QM; the first investigation moves the incident to investigating |
| `action_check` | corrective_action | No new actions on closed incidents; active assignee |
| `audit_*` (8 triggers) | batch, shipment, incident, incident_batch, investigation, corrective_action, staff, sensor_reading | The generic `trg_audit()`, a SECURITY DEFINER function, writes old and new rows (without password hashes), the acting user and the reason |

**Excursion detection.** For every valid reading, `reading_evaluate` does the following:

1. Finds the sensor's assignment at the reading's time.
2. Finds the batches present there: the shipment's lines, or the facility's stock at that time.
3. Compares the reading with **each batch's own product limits**.
4. **On a breach,** `record_excursion()`:
   - takes an advisory lock per target, so two readings cannot both open an incident;
   - finds or creates the active incident;
   - links the reading and the breached batches;
   - raises the severity, never lowering it.

   The illustrative severity thresholds, by distance beyond the limit, are: up to 1 °C low, up to 3 °C medium, up to 5 °C high, above 5 °C critical.
5. **When readings return within limits,** `end_excursion()` records the end time.

### Views (`05_views.sql`)

There are 14 views, so every derived number comes from SQL:

| Group | Views |
|---|---|
| Stock and status | `v_batch_stock`, `v_batch_in_transit`, `v_batch_summary` (on hand, in transit, days to expiry, open incidents) |
| Shipments | `v_shipment_limits` (tightest range on board), `v_shipment_summary` (with an overdue flag) |
| Incidents | `v_incident_exposure` (exposure from the linked readings, peak, number of breaching readings), `v_incident_summary` |
| Dashboard | `v_dashboard` (seven counters) |
| Reports | `v_report_incidents_by_type_severity`, `v_report_batch_incidents`, `v_report_vehicle_repeat_incidents` (`HAVING COUNT > 1`), `v_report_pending_actions`, `v_report_expiring_batches`, `v_report_sensor_quality` (gaps found with `LAG()`) |

### Privileges (`06_grants.sql`)

The application role `pharmatrace_app`:

- has SELECT on all tables;
- has INSERT and UPDATE on business tables;
- can DELETE only shipment lines and facility phone numbers;
- on readings, can INSERT and can UPDATE only `quality_status`;
- has **no** write access to `audit_log` or `batch_status_transition`.

## 5.3 Backend implementation

| Module | Responsibility |
|---|---|
| `config.py` | Settings from `.env` (pydantic-settings) |
| `db.py` | Connection pool; one transaction per request; `set_context()` sets `app.current_staff_id` and `app.change_reason` |
| `auth.py` | Argon2 password check; JWT (HS256) issue and verify; `require(*roles)`; the `Db` dependency |
| `errors.py` | Maps PostgreSQL errors to HTTP (403, 404, 409, 422) with readable messages |
| `routers/catalog.py` | Products, batches (including trace and status), facilities, vehicles, sensors, assignments, staff |
| `routers/shipments.py` | Create, add or remove lines, dispatch, receive, cancel, checkpoints, timeline |
| `routers/monitoring.py` | Idempotent reading ingestion; filtered reading queries |
| `routers/incidents.py` | Incidents, investigations, batch assessments, corrective actions, status changes |
| `routers/reports.py` | Dashboard, reports (whitelisted view names), audit log, simulator |
| `simulator.py` | Normal readings for active sensors; a scripted refrigeration failure (14 readings, 2.5 s apart) |

All 50 endpoints are listed in Appendix B.

## 5.4 Frontend implementation

The frontend has 12 pages behind a role-aware navigation bar:

| Page | Function |
|---|---|
| Login | Email and password, with validation; demonstration-account helper |
| Dashboard | Seven live counters, shipments in transit, recent incidents; administrator simulator panel |
| Shipments / Shipment detail | List, create (with lines and sensor), dispatch, receive, cancel, checkpoints, timeline, incidents |
| Batches / Batch trace | Search and register; stock per facility, chain of custody, shipments, incidents, decision history, decision form |
| Products | List and register with limits |
| Monitoring | Readings by sensor or shipment, time window, quality filter, out-of-limits filter, chart with limit lines |
| Incidents / Incident detail | List and manual report; chart, exposure, affected batches, assessments, decisions, investigation, actions, related shipments, audit history, status changes |
| Reports | Six tabbed SQL reports |
| Facilities & admin | Facilities (with phones), vehicles, sensors (with installation), staff (admin only), audit log (QM and admin only) |

Display codes such as SH001 and INC0001 are formatted from integer keys and never stored.

## 5.5 Demonstration data

`scripts/seed.py` loads the following:

| Data | Contents |
|---|---|
| Staff | Five staff members across all four roles |
| Products | Four products: three at 2–8 °C, and Tablet D at 15–25 °C, 30–65 % RH |
| Facilities | Six facilities across Karnataka |
| Vehicles | Four vehicles, one with degraded refrigeration |
| Batches | Twelve batches, one already expired and one expiring within 20 days |
| Sensors | Ten sensors: one installed at a distribution centre, one inactive, one faulty |
| Shipments | Six shipments covering every status |
| Readings | About 6,000, including a 40-minute gap and one corrupt value |

The data also includes two incidents:

- **INC0001** is closed. Its investigation is complete, batch B004 was released and B003 disposed, and two corrective actions are done.
- **INC0002** is under investigation, with batch B005 on hold and one overdue corrective action.

Every step of the demonstration data was created through the same functions and triggers the application uses.


# 6. Design of Forms, Security and Validation

## 6.1 Three layers of validation

Every input is checked three times. A rule that the browser misses, for example from a direct API call or a script, is still enforced by the API, and finally by the database.

| Layer | Technology | What it checks | User sees |
|---|---|---|---|
| 1. Browser form | Mantine `useForm` validators | Required fields, formats, ranges, cross-field rules | A red message under the field; the form is not submitted |
| 2. API | Pydantic models with field constraints and validators | Types, ranges, patterns, cross-field rules; roles | HTTP 422 with the field and message, or 403 for a role; shown as a toast |
| 3. Database | CHECK, UNIQUE, FOREIGN KEY, EXCLUDE constraints and triggers | Integrity and workflow rules | HTTP 409 or 422 with the database's readable message, shown as a toast |

## 6.2 Forms

| Form (page) | Fields | Browser validation | API validation | Database enforcement |
|---|---|---|---|---|
| Login | Email, password | Valid email format; password required | Credentials checked against an Argon2 hash; HTTP 401 if wrong | Only `active` accounts can log in |
| New shipment (Shipments) | Origin, destination, vehicle, expected arrival, sensor, batch lines (batch, quantity) | All required; destination ≠ origin; arrival in the future; a batch and a quantity > 0 on each line | Arrival in the future; quantity 1–10,000,000 | `shipment_route`; foreign keys; `shipment_batch_check` (shipment planned, product ranges overlap); unique line per batch |
| Register batch (Batches) | Batch number, product, manufactured, expires, quantity, received-at facility | Number matches `[A-Za-z0-9-_/]{2,40}`; manufacture not in the future; expiry after manufacture; quantity > 0 | Same rules in Pydantic | UNIQUE batch_number; `batch_dates`; quantity CHECK; intake movement in the same transaction |
| Register product (Products) | Name, type, min/max °C, optional min/max % RH | Name required; max > min; humidity limits valid | −80…80 °C; humidity 0–100; min < max; both-or-neither | `product_temp_range`, `product_humidity_pair`, `product_humidity_range`; UNIQUE name |
| Add facility (Admin) | Name, type, street, city, PIN code, phone numbers | Required fields; PIN = 6 digits not starting with 0; phone characters | Same patterns | PIN-code and phone CHECKs; UNIQUE name; multivalued phones in FACILITY_PHONE |
| Add vehicle / sensor (Admin) | Registration and type; serial number and type | Registration upper-cased; serial ≥ 3 characters | Registration pattern; types from fixed lists | UNIQUE registration and serial; type CHECKs |
| Staff account (Admin) | Name, email, password, role | Email format; password ≥ 8 characters | Same; administrator only | UNIQUE `lower(email)`; role CHECK |
| Report incident (Incidents) | Target (shipment or facility), type, severity, start, description | A target chosen; description ≥ 5 characters | Exactly one target; types and severities from fixed lists | `incident_one_target`, `incident_manual_reporter` |
| Record decision (Batch trace, Incident) | New status, reason | Only the transitions allowed for the user's role are offered; reason ≥ 3 characters | Investigator or QM only | `trg_batch_status_check` against BATCH_STATUS_TRANSITION |
| Assess batch (Incident) | Assessment, note | Note required when "assessed" | Values from a fixed list | `assessed_needs_note` |
| Corrective action (Incident) | Description, responsible person, due date | Description ≥ 5 characters; responsible person required | Investigator or QM to add; assignee, investigator or QM to update | Description CHECK; active assignee; no actions on closed incidents |
| Incident status (Incident) | Status, reason | Reason ≥ 3 characters | Investigator or QM | `trg_incident_lifecycle` (allowed moves; closing rules; QM only) |
| Checkpoint (Shipment) | Event type, location | Location ≥ 2 characters | Only while the shipment is in transit | Event type CHECK; key is (shipment, checkpoint_no) |

![Validation on the new-shipment form](screenshots/15_form_new_shipment_validation.png){width=85%}

*Figure 6.1: New-shipment form submitted empty: each required field shows its message, and nothing is saved.*

![Validation on the batch form](screenshots/16_form_register_batch_validation.png){width=85%}

*Figure 6.2: Register-batch form: an invalid batch number and an expiry date before manufacture are rejected.*

![Validation on the product form](screenshots/17_form_new_product_validation.png){width=85%}

*Figure 6.3: Product form: a maximum temperature below the minimum is rejected.*

![Validation on the facility form](screenshots/18_form_facility_validation.png){width=85%}

*Figure 6.4: Facility form: a PIN code starting with 0 is rejected.*

## 6.3 Authentication

- **Passwords** are stored only as **Argon2** hashes (pwdlib). Plain-text passwords are never stored or logged. Hashes are excluded from every API response and from the audit log (the audit trigger removes the `password_hash` field).
- **Sessions.** A successful login returns a **JWT** (HS256) signed with the server secret and valid for 8 hours. Every API call requires it. An invalid or expired token returns HTTP 401, and the web app returns to the login page.
- **Inactive accounts** cannot log in, and their existing tokens stop working.

![Wrong password](screenshots/01b_login_wrong_password.png){width=70%}

*Figure 6.5: A wrong password is refused (HTTP 401).*

## 6.4 Authorisation (role-based access control)

| Action | Operator | Investigator | Quality manager | Admin |
|---|---|---|---|---|
| Register products, batches, facilities, vehicles, sensors; create shipments | ✓ | | ✓ | ✓ |
| Dispatch, receive, cancel shipments; add checkpoints | ✓ | | | ✓ |
| Report a manual incident | ✓ | ✓ | ✓ | |
| Record findings, assess batches, put a batch on hold, add corrective actions | | ✓ | ✓ | |
| Assign investigators; quarantine, release, return or dispose batches; close incidents | | | ✓ | |
| Complete a corrective action | its assignee | ✓ | ✓ | |
| Manage staff; run the simulator | | | | ✓ |
| Read the audit log | | | ✓ | ✓ |
| Read everything else | ✓ | ✓ | ✓ | ✓ |

Roles are enforced in three places:

1. **The interface** hides actions a role cannot take. This is a convenience only.
2. **The API** checks the role on every endpoint and returns HTTP 403.
3. **The database** re-checks the rules that matter most, using the acting user recorded for the transaction (`app.current_staff_id`):
   - batch status transitions come from the BATCH_STATUS_TRANSITION table;
   - only a quality manager can close an incident;
   - only an investigator or QM can be assigned an investigation.

Test TC26 shows that an operator is refused by **both** the API and the database.

![Operator view](screenshots/19a_role_operator_batch_no_decision_button.png){width=80%}

*Figure 6.6: An operator sees no "Record decision" button on a batch.*

![Investigator transitions](screenshots/19c_role_investigator_only_allowed_transitions.png){width=80%}

*Figure 6.7: An investigator is offered only the transitions their role allows (available → on hold).*

## 6.5 Database-level security

- **Least privilege.** The API connects as `pharmatrace_app`, which cannot delete readings, write the audit log, change the workflow rules or truncate tables (TC28). Schema changes are made by `pharmatrace_owner`.
- **Immutable evidence.** Sensor readings cannot be updated or deleted, except for their quality flag (TC23).
- **Audit trail.** A generic trigger records every change to batches, shipments, incidents, assessments, investigations, corrective actions, staff, and reading quality flags. Each entry holds the old and new values, the acting user, the time, and the reason the user typed.
  - The trigger runs as `SECURITY DEFINER` with a fixed `search_path`, so it can write the log even though the application role cannot.
- **SQL injection.** Every query is parameterised (psycopg placeholders). The report endpoint accepts only names from a fixed list of views (TC27).
- **CORS.** The API accepts browser requests only from the configured frontend origin.
- **Secrets.** Database passwords and the JWT secret live in `.env`, which is excluded from version control.


# 7. Testing

## 7.1 Strategy

| Level | What is tested | Tool | Result |
|---|---|---|---|
| Database (unit) | Keys, constraints, triggers, functions, views, privileges, run directly against PostgreSQL | pytest + psycopg | Pass |
| Transactions and concurrency | Atomic dispatch and receipt, rollback on partial failure, two simultaneous sessions | pytest with two real connections and threads | Pass |
| API (integration) | Login, tokens, role checks, validation, error mapping, full workflow over HTTP | pytest + FastAPI TestClient | Pass |
| Evidence run (TC01–TC34) | Every lab-manual test case on a fresh database, recording the **actual** system response | `backend/scripts/evidence.py` | 34 / 34 pass |
| End-to-end (UI) | Every page as every role (no console errors); the full demonstration scenario through the browser | Playwright driving Microsoft Edge (`tools/e2e/`) | Pass |

Test design used equivalence partitioning and boundary values: quantity 0 and 1; expiry one day after manufacture; a reading exactly beyond the limit; future timestamps. Every constraint was given both a positive and a negative case.

**Test environment:**

- PostgreSQL 18 in a separate database (`pharmatrace_test` for pytest, `pharmatrace_evidence` for the evidence run), rebuilt from the SQL scripts;
- Python 3.12;
- Windows 11.

**Test data:** each test starts from the same small data set:

- 4 staff members (one per role);
- 3 products: a vaccine at 2–8 °C, a syrup at 2–25 °C and a tablet at 15–25 °C;
- 3 facilities and 1 vehicle;
- batches B1–B4, plus BEXP, which has already expired;
- 3 sensors.

## 7.2 Results summary

| Module | Test cases | Passed |
|---|---|---|
| Product | TC01, TC02, TC06 | 3 / 3 |
| Batch | TC03, TC04, TC05 | 3 / 3 |
| Shipment | TC07, TC08, TC09, TC10 | 4 / 4 |
| Transaction | TC11, TC12, TC13, TC15 | 4 / 4 |
| Concurrency | TC14 | 1 / 1 |
| Monitoring | TC16, TC17, TC18, TC19, TC20, TC21, TC22, TC23 | 8 / 8 |
| Incident | TC24 | 1 / 1 |
| Security | TC25, TC26, TC27, TC28 | 4 / 4 |
| Investigation | TC29, TC30, TC31 | 3 / 3 |
| Reports | TC32, TC33 | 2 / 2 |
| Forms | TC34 | 1 / 1 |
| **Total (lab-manual test cases)** | TC01–TC34 | **34 / 34** |
| **Automated pytest suite** | 5 files | **68 / 68** |

![Test cases by module](figures/tests_by_module.png){width=85%}

*Figure 7.1: Lab-manual test cases TC01–TC34 by module (evidence run).*

![Automated suite](figures/tests_pytest_by_file.png){width=85%}

*Figure 7.2: The automated pytest suite, by file.*

## 7.3 Test cases with actual results

The table below is generated from `docs/final-report/evidence/test_evidence.json`. The **Actual result** column is the system's real output: the exact PostgreSQL error, the row counts or the HTTP response. Appendix C lists every case in full.

| TC | Module | Test | Input / action | Expected | Actual result (system output) | Status |
|---|---|---|---|---|---|---|
| TC01 | Product | Register a valid product | INSERT product 'Vaccine X', vaccine, 2.00-8.00 °C | Product saved; new product_id returned | Saved: product_id=4 | Pass |
| TC02 | Product | Invalid temperature range rejected | INSERT product with min_temp 8, max_temp 2 | Rejected by CHECK (min_temp < max_temp) | CheckViolation: new row for relation "product" violates check constraint "product_temp_range" [constraint product_temp_range] | Pass |
| TC03 | Batch | Duplicate batch number rejected | INSERT a second batch with number B1 | Second insert rejected (UNIQUE) | UniqueViolation: duplicate key value violates unique constraint "batch_batch_number_key" [constraint batch_batch_number_key] | Pass |
| TC04 | Batch | Expiry before manufacture rejected | INSERT batch mfg 2026-05-01, expiry 2026-04-01 | Rejected by CHECK (expiry_date > manufacturing_date) | CheckViolation: new row for relation "batch" violates check constraint "batch_dates" [constraint batch_dates] | Pass |
| TC05 | Batch | Quantity boundary | INSERT batch with initial_quantity 0, then 1 | 0 rejected; 1 accepted | Quantity 0 -> CheckViolation: new row for relation "batch" violates check constraint "batch_initial_quantity_check" [constraint batch_initial_quantity_check]. Quantity 1 -> saved (batch_id=7) | Pass |
| TC06 | Product | Product with batches cannot be deleted | DELETE product 'Vaccine A' (has batches) | Rejected by foreign key (ON DELETE RESTRICT) | RestrictViolation: update or delete on table "product" violates RESTRICT setting of foreign key constraint "batch_product_id_fkey" on table "batch" [constraint batch_product_id_fkey] | Pass |
| TC07 | Shipment | Shipment with nonexistent vehicle rejected | INSERT shipment with vehicle_id 999 | Rejected by foreign key | ForeignKeyViolation: insert or update on table "shipment" violates foreign key constraint "shipment_vehicle_id_fkey" [constraint shipment_vehicle_id_fkey] | Pass |
| TC08 | Shipment | Same origin and destination rejected | INSERT shipment Warehouse -> Warehouse | Rejected by CHECK (origin <> destination) | CheckViolation: new row for relation "shipment" violates check constraint "shipment_route" [constraint shipment_route] | Pass |
| TC09 | Shipment | Add batch to shipment | INSERT shipment_batch (shipment, B1, 1000) | Row saved in SHIPMENT_BATCH | Saved: shipment 1 carries B1 x 1000 | Pass |
| TC10 | Shipment | Same batch twice in one shipment rejected | INSERT shipment_batch B1 again for the same shipment | Rejected (composite primary key) | UniqueViolation: duplicate key value violates unique constraint "shipment_batch_pkey" [constraint shipment_batch_pkey] | Pass |
| TC11 | Transaction | Dispatch a shipment | SELECT dispatch_shipment() for B1 x400 + B2 x100 with sensor attached | Status in_transit; dispatch movements and departure checkpoint recorded; stock reduced | status=in_transit; dispatched movements=2; checkpoint=departure; B1 stock at origin 1000 -> 600 | Pass |
| TC12 | Transaction | Partial failure rolls back the whole dispatch | dispatch_shipment() with B1 x100 (in stock) and B2 x9999 (only 500 in stock) | Error raised; no movement kept for B1 or B2; status stays planned | RaiseException: Insufficient stock of batch B2: 500 at origin, 9999 requested. Afterwards: movements for this shipment=0, status=planned, B1 stock=1000 (unchanged) | Pass |
| TC13 | Transaction | Expired or quarantined batch cannot be dispatched | dispatch_shipment() with an expired batch; then with a quarantined batch | Dispatch rejected with a message | Expired: RaiseException: Batch BEXP expired on 2026-11-07; it cannot be dispatched. Quarantined: RaiseException: Batch B1 is quarantined; it cannot be dispatched | Pass |
| TC14 | Concurrency | Two concurrent dispatches cannot oversell stock | Two sessions each dispatch 800 of the 1,000 units of B1 at the same time | One commits, the other fails; stock never negative | Session 1 committed. Session 2 waited for the row lock (waiting=True), then: RaiseException: Insufficient stock of batch B1: 200 at origin, 800 requested. Final B1 stock at origin = 200 | Pass |
| TC15 | Transaction | Receive a shipment | dispatch_shipment() then receive_shipment() for B1 x300 | Status delivered; stock moved to destination; sensor assignment closed | status=delivered; B1 stock at destination=300; open sensor assignments=0 | Pass |
| TC16 | Monitoring | Overlapping sensor assignment rejected | Assign sensor S1 to a second shipment while it is still attached to the first | Rejected (EXCLUDE constraint) | ExclusionViolation: conflicting key value violates exclusion constraint "assignment_no_overlap" [constraint assignment_no_overlap] | Pass |
| TC17 | Monitoring | Valid reading inside limits | Reading 5.2 °C from S1 on a dispatched shipment | Reading saved as valid; no incident | reading_id=1 stored, quality=valid; incidents=0 | Pass |
| TC18 | Monitoring | Reading outside limits raises an incident | Readings 5.2 °C, then 8.6 °C (vaccine limit 8 °C) | Reading saved; incident created and linked to shipment, reading and batch | 1 incident: id=1, type=temperature_excursion, shipment=1, source=automatic, status=open, severity=low; breaching reading linked=True | Pass |
| TC19 | Monitoring | Repeated breach appends to the same incident | Readings 8.6 °C then 12.5 °C | Same open incident; severity raised; no new incident | incidents=1; severity low -> high; linked readings=2 | Pass |
| TC20 | Monitoring | Duplicate reading rejected | Same sensor and timestamp inserted twice | Rejected (UNIQUE sensor_id, recorded_at) | UniqueViolation: duplicate key value violates unique constraint "reading_unique_per_sensor" [constraint reading_unique_per_sensor] | Pass |
| TC21 | Monitoring | Future timestamp stored as invalid | Reading 20 °C recorded 2 hours in the future | Stored with quality invalid; no incident | reading_id=1 stored, quality=invalid; incidents=0 | Pass |
| TC22 | Monitoring | Missing readings appear in the data-quality report | Readings at -45, -40, -35, -5, 0 min (5-minute sensor) -> a 30-minute hole | Gap shown in the sensor quality report | v_report_sensor_quality for S1: gaps=1, longest_gap_minutes=30 | Pass |
| TC23 | Monitoring | Original reading values are protected | UPDATE the temperature of a stored reading; DELETE it; UPDATE only its quality flag | Value change and delete rejected by trigger; quality flag change allowed | UPDATE value -> RaiseException: Original values of reading 1 cannot be changed; only quality_status may be updated. DELETE -> RaiseException: Sensor readings cannot be deleted (reading 1). Quality flag update -> allowed; temperature still 5.00 | Pass |
| TC24 | Incident | Trace affected batches | Reading 10.1 °C on a shipment carrying vaccine (2-8 °C) and syrup (2-25 °C) | Only the batches whose own limits were breached are linked | Linked batches: ['B1'] (B3 syrup, limit 25 °C, correctly not linked) | Pass |
| TC25 | Security | Login with a wrong password | POST /api/auth/login with a valid email and a wrong password | 401 Unauthorized; no token issued | Wrong password -> HTTP 401 {'detail': 'Incorrect email or password'}. Correct password -> HTTP 200 with a token | Pass |
| TC26 | Security | Unauthorised status change rejected (API and database) | Operator calls POST /api/batches/B1/status 'released'; operator context runs the UPDATE directly in SQL | Rejected by the API (403) and by the database trigger | API -> HTTP 403 {'detail': 'Requires role: investigator, quality_manager'}. Direct SQL -> InsufficientPrivilege: Role operator may not change batch B1 from available to on_hold | Pass |
| TC27 | Security | SQL injection attempt | GET /api/batches?q=' OR 1=1 -- | Treated as plain text; no extra rows | All batches: 5 rows. Injection string -> HTTP 200, 0 rows (searched literally) | Pass |
| TC28 | Security | Application role cannot delete readings or write the audit log | As pharmatrace_app: DELETE FROM sensor_reading; INSERT INTO audit_log | Permission denied | DELETE readings -> InsufficientPrivilege: permission denied for table sensor_reading. INSERT audit_log -> InsufficientPrivilege: permission denied for table audit_log | Pass |
| TC29 | Investigation | Complete an investigation | Mark investigation completed without findings; then with findings | Rejected without findings; with findings completed_at is recorded | Without findings -> CheckViolation: new row for relation "investigation" violates check constraint "investigation_findings" [constraint investigation_findings]. With findings -> completed (completed_at recorded=True) | Pass |
| TC30 | Investigation | Closing an incident too early is refused | Resolve the incident, then close it while a corrective action is pending (and batches unassessed) | Rejected with the reason shown | With a pending action -> RaiseException: Incident 1 has corrective actions that are not finished. With the action done but batches unassessed -> RaiseException: Incident 1 has affected batches that are not assessed | Pass |
| TC31 | Investigation | Close a fully resolved incident | All work done; investigator tries to close; quality manager closes | Only the QM can close; status closed; audit entry | Investigator -> InsufficientPrivilege: Only a quality manager can close an incident. Quality manager -> closed. Latest audit entry: incident_status=closed, changed_by=Quality Manager | Pass |
| TC32 | Reports | Dashboard counts match base tables | Compare v_dashboard with direct COUNT queries | Every dashboard number equals the matching SQL count | v_dashboard (active shipments, open incidents, batches under investigation) = (1, 1, 2); direct counts = (1, 1, 2) | Pass |
| TC33 | Reports | Incident report totals match | SUM of v_report_incidents_by_type_severity vs COUNT(*) FROM incident | Report total equals the table count | Report total=1; COUNT(*) FROM incident=1 | Pass |
| TC34 | Forms | Required-field and range validation | POST /api/shipments without destination; POST /api/products with min 8 > max 2 | 422 with a message naming the problem; nothing saved | Shipment -> HTTP 422, missing fields ['destination_facility_id', 'expected_arrival']. Product -> HTTP 422, 'Value error, Minimum temperature must be below maximum temperature'. Shipments saved: 0 | Pass |

## 7.4 Selected proofs explained

- **TC12, rollback.** The dispatch processed B1 first, then failed on B2 ("Insufficient stock of batch B2"). Afterwards, the shipment had zero movements and was still *planned*, and B1's stock was unchanged at 1,000. So the whole dispatch was undone, including the part that had already succeeded.
- **TC14, concurrency.** Session 1 dispatched 800 of B1's 1,000 units and held the row lock. Session 2 tried to dispatch another 800 and **waited** for that lock. When session 1 committed, session 2 re-read the stock (200) and failed cleanly. The final stock was 200: never negative, and no unit was sold twice.
- **TC24, precise tracing.** A 10.1 °C reading on a shipment carrying a vaccine (limit 8 °C) and a syrup (limit 25 °C) linked **only** the vaccine batch. The system does not condemn every batch on board.
- **TC26, defence in depth.** The operator's request was refused by the API (HTTP 403). The same change attempted directly in SQL, as that operator, was refused by the database trigger ("Role operator may not change batch B1 from available to on_hold").
- **TC30, workflow rule.** Closing was refused twice, with a specific reason each time: first because a corrective action was still pending, then because the affected batches were not assessed.

## 7.5 Automated test suite

All 68 automated tests pass (`uv run pytest`, last run on the date of this report):

| File | Tests | Passed | Test names |
|---|---|---|---|
| test_api.py | 11 | 11 | `test_tc25_wrong_password_rejected`, `test_requests_need_a_token`, `test_tc26_operator_cannot_change_batch_status`, `test_tc26_database_rule_applies_even_to_allowed_api_roles`, `test_tc27_sql_injection_is_plain_text`, `test_tc34_validation_messages`, `test_db_errors_become_readable_responses`, `test_end_to_end_incident_workflow`, `test_reports_and_dashboard_available`, `test_admin_only_endpoints`, `test_owner_sees_hashes_not_in_api` |
| test_db_constraints.py | 19 | 19 | `test_tc01_valid_product_saved`, `test_tc02_invalid_temperature_range_rejected`, `test_humidity_limits_must_come_in_pairs`, `test_tc03_duplicate_batch_number_rejected`, `test_tc04_expiry_before_manufacture_rejected`, `test_tc05_quantity_boundary`, `test_tc06_product_with_batches_cannot_be_deleted`, `test_tc07_nonexistent_vehicle_rejected`, `test_tc08_same_origin_and_destination_rejected`, `test_tc09_add_batch_to_shipment`, `test_tc10_same_batch_twice_rejected`, `test_incompatible_storage_ranges_rejected`, `test_status_and_timestamps_must_agree`, `test_tc16_overlapping_sensor_assignment_rejected`, `test_assignment_needs_exactly_one_target`, `test_tc28_app_role_cannot_delete_readings_or_audit`, `test_pincode_format`, `test_unique_email_case_insensitive`, `test_check_constraints_use_dates` |
| test_db_monitoring.py | 13 | 13 | `test_tc17_valid_reading_in_range_no_incident`, `test_tc18_out_of_limit_reading_creates_incident`, `test_tc24_only_breached_batches_are_linked`, `test_tc19_repeated_breach_appends_and_escalates`, `test_recovery_sets_end_time_and_new_breach_reopens_window`, `test_tc20_duplicate_reading_rejected`, `test_tc21_future_timestamp_stored_as_invalid_without_incident`, `test_implausible_value_kept_but_invalid`, `test_faulty_sensor_readings_are_suspicious`, `test_tc22_gap_appears_in_quality_report`, `test_tc23_original_reading_values_are_protected`, `test_facility_excursion_uses_stock_at_that_time`, `test_reading_from_unassigned_sensor_is_stored_only` |
| test_db_transactions.py | 10 | 10 | `test_tc11_dispatch_records_movements_checkpoint_and_status`, `test_tc12_partial_failure_rolls_back_everything`, `test_tc13_expired_batch_cannot_be_dispatched`, `test_tc13_quarantined_batch_cannot_be_dispatched`, `test_dispatch_requires_sensor`, `test_dispatch_blocked_for_faulty_vehicle`, `test_lines_frozen_after_dispatch`, `test_tc14_concurrent_dispatches_cannot_oversell`, `test_tc15_receive_moves_stock_and_closes_assignment`, `test_receive_requires_in_transit` |
| test_db_workflow.py | 15 | 15 | `test_tc26_operator_cannot_release_batch`, `test_status_change_needs_staff_context`, `test_investigator_may_hold_but_not_release`, `test_disposed_is_terminal`, `test_assigning_investigation_moves_incident_to_investigating`, `test_operator_cannot_be_assigned_investigation`, `test_tc29_complete_investigation_requires_findings`, `test_cannot_resolve_with_open_investigation`, `test_tc30_cannot_close_with_pending_action_or_unassessed_batch`, `test_tc31_close_fully_resolved_incident`, `test_incident_cannot_skip_states`, `test_tc32_dashboard_matches_base_tables`, `test_tc33_incident_report_totals_match`, `test_audit_log_never_stores_password_hash`, `test_related_shipments_same_vehicle` |

## 7.6 End-to-end tests through the user interface

Two browser scripts drive the real application in Microsoft Edge:

- **Page sweep (`check.mjs`).** It logs in as each of the four roles and opens all 13 page routes. Any browser console error or server error counts as a failure. Result: **52 of 52 page/role combinations clean.**
- **Demonstration scenario (`demo.mjs` and `report_shots.mjs`).** It performs the complete incident workflow through the user interface, as four different users:
  1. simulate a failure;
  2. the database raises the incident;
  3. assign an investigator;
  4. assess the batches, hold one, add an action, record findings;
  5. try to close too early (refused);
  6. complete the action;
  7. release the batch and close.

  Result: **the flow completes**. Every step is shown in Chapter 8.

Two interface defects were found and fixed during this testing:
- invalid HTML nesting in page subtitles;
- table columns clipped inside half-width cards.

One misleading attribution was also corrected: automatically raised incidents are now shown as created by "automatic detection".


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


# 9. Innovative Experiment: Learned Index under Cold-Chain Workloads

## 9.1 Question

Sensor readings in PharmaTrace are looked up by (sensor, time). During a refrigeration failure the workload shifts in three ways:

- a few sensors start reporting far more often;
- investigators query a narrow time window again and again;
- later, activity returns to normal.

The questions are:

1. Does a learned index, ALEX [7], keep its advantage over a B+ tree under such shifts?
2. What does adapting to the shifts cost?
3. Can a simple policy reduce that cost?

The benchmark runs on its own, outside PostgreSQL. It evaluates the index structures on workloads modelled on the application; it does not change how the application's own SQL runs.

## 9.2 Method

| Item | Setting |
|---|---|
| Keys | `sensor_id << 40 | epoch_seconds`: unique, ordered by sensor then time; 8-byte payload |
| Initial data | 1,000 sensors × 30 days at 5-minute intervals = **8,640,000 keys**, bulk-loaded |
| Workload | Six phases × 1,000,000 operations, generated once (fixed seed); **every configuration replays identical files** |
| Configurations | B+ tree (tlx `btree_map`, commit 2dd63ab); ALEX (`alex::Alex`, commit 4370da6); **ALEX-HB** (proposed, section 9.4); ALEX-HB without migration (ablation) |
| Build and run | g++ 14.4, `-O3 -march=native`, single thread, in Docker on WSL2; AMD Ryzen 5 7535HS; 5 repetitions per configuration, each in a fresh process, with the run order rotated |
| Measurements | Each operation timed individually (20 ns timer overhead included); throughput; p50/p95/p99/p99.9/maximum latency; share of time in the slowest 1 %; memory (RSS); ALEX's internal counters |
| Correctness | Lookup hits and payload checksums were **identical** for every configuration and repetition |

| Phase | Simulates | Operation mix |
|---|---|---|
| P1 stable | Normal monitoring | 80 % lookups, 10 % inserts (all sensors, 5-minute steps), 10 % one-hour range scans |
| P2 ingestion spike | Many more readings | 60 % inserts, 35 % lookups, 5 % ranges |
| P3 localised incident | 10 failing sensors report every second | 50 % inserts on those sensors, 50 % lookups |
| P4 investigation | Repeated queries on the incident window | Zipf(0.99) over incident readings: 47.5 % lookups, 47.5 % ten-minute ranges, 5 % inserts |
| P5 recovery | Back to normal | Same mix as P1 |
| P6 combined shift | A second failure while it is being investigated | 50 % inserts on 10 new sensors, 50 % lookups of their newest readings |

## 9.3 Baseline: ALEX against the B+ tree

**Reads favour ALEX.**
- P1 lookups: median 231 ns for ALEX against 521 ns for the B+ tree.
- P4 lookups: 101 ns against 321 ns.
- P4 ten-minute range scans: 762 ns against 3,717 ns.

**ALEX's insert cost is concentrated in rare reorganisations.**
- In P1, P3 and P6, its slowest 1 % of inserts took 81–84 % of all its insert time.
- Its worst single insert pauses were 27 ms (P1), 37.5 ms (P3) and 23 ms (P6). The B+ tree's worst was 0.44 ms (P4).
- ALEX's own counters show the adaptation work arriving in bursts at the distribution shifts: expand-and-scale operations went 0 → 206 → 619 → 1,008 across the phases.

**Memory and loading.**
- After all phases, ALEX used 510 MB against the B+ tree's 244 MB.
- Its bulk load was slower: 104 ns against 17 ns per key.

## 9.4 Proposed policy: ALEX-HB (hot-range buffer)

ALEX-HB absorbs hot-spot inserts in a small B+ tree placed in front of ALEX, and moves them into ALEX later, once the hot spot has cooled.

- **Detect hot sensors.** Over the last W = 4,096 inserts, a sensor with H = 64 or more inserts is *hot*. It cools when its count falls below 32.
- **Route inserts.** Hot sensors' inserts go into the buffer; all others go straight into ALEX.
- **Read from both.** A lookup checks the buffer only if the key's sensor has buffered keys. A range scan adds the results of both structures; each key lives in exactly one.
- **Deferred migration.** While no sensor is hot, each operation moves up to M = 4 buffered keys into ALEX. The cost is counted in that operation's measured time.

Update buffers placed in front of learned indexes appear in earlier designs (for example XIndex and FINEdex). What is tested here is a hot-sensor trigger with deferred migration, under incident-driven workloads.

## 9.5 Results (throughput, million operations per second, median of 5 repetitions)

| Phase | B+ tree | ALEX | **ALEX-HB** | ALEX-HB, no migration |
|---|---|---|---|---|
| P1 stable | 1.53 | 2.05 | 2.02 | 2.04 |
| P2 ingestion spike | 2.38 | 2.05 | 2.13 | 2.08 |
| P3 localised incident | 2.59 | 2.66 | **4.35** | 4.37 |
| P4 investigation | 0.46 | **1.79** | 0.89 | 0.42 |
| P5 recovery | 1.79 | 3.40 | 3.29 | 3.26 |
| P6 combined shift | 6.98 | 3.57 | **8.49** | 8.25 |

![Throughput, four configurations](figures/bench_throughput_4configs.png){width=100%}

*Figure 9.1: Throughput per phase. Whiskers show the minimum and maximum of the 5 repetitions.*

| Insert latency | ALEX p99.9 | ALEX worst | ALEX-HB p99.9 | ALEX-HB worst | Time in the slowest 1 %: ALEX → ALEX-HB |
|---|---|---|---|---|---|
| P3 localised incident | 3,466 ns | 37.5 ms | 581 ns | 0.10 ms | 81 % → 5 % |
| P6 combined shift | 2,596 ns | 23.4 ms | 541 ns | 0.07 ms | 84 % → 5 % |

![Latency](figures/bench_latency_4configs.png){width=100%}

*Figure 9.2: Lookup latency (left) and the insert tail: p99.9 and worst pause (right), on log scales.*

| Memory above baseline (MB) | After P3 | After P4 | After P6 |
|---|---|---|---|
| B+ tree | 216 | 221 | 244 |
| ALEX | 410 | 413 | 510 |
| ALEX-HB | 302 | 408 | 409 |
| ALEX-HB, no migration | 302 | 307 | 308 |

![Memory](figures/bench_memory_4configs.png){width=75%}

*Figure 9.3: Index memory after each phase.*

## 9.6 Analysis

**Where ALEX-HB wins.** In both incident phases, ALEX's long reorganisation pauses disappear:

- In **P3**, throughput is 1.64× plain ALEX, and the worst insert falls from 37.5 ms to 0.1 ms.
- In **P6**, throughput is 2.4× plain ALEX. ALEX-HB is the fastest of all four configurations, 1.22× the B+ tree.
- After P6, it uses 101 MB less memory than ALEX.

**Where it loses.**

- **Migration lands on the investigation.** During P3, the buffer collected about 499,000 keys from the 10 hot sensors. In P4 no sensor is hot, so migration begins, and it overlaps exactly with investigators querying those same keys:
  - P4 throughput halves (0.89 against 1.79 million operations per second for ALEX), though it remains 1.9× the B+ tree;
  - lookup p99.9 rises to 15.7 µs, with pauses up to 18 ms, because ALEX's node expansions now happen during migration instead of during the burst.
- **Without migration,** P4 is slower still (0.42), because every investigation query also searches the large buffer.
- **Slower migration did not help.** A sensitivity run with M = 1 (3 repetitions) gave 0.63 in P4, worse than with M = 4, because migrating more slowly lengthens the overlap with the queries.
- **P1, P2 and P5 are unchanged**, as expected: no sensor becomes hot in those phases.

**Conclusion.** Buffering hot ranges removes ALEX's pauses during insert bursts. The limiting factor is *when* the buffered keys are merged back. Two directions follow from the measurements, and neither has been tested yet:

- **faster migration:** merge a cooled sensor's range in one step, for example by bulk-loading a new ALEX node;
- **query-aware migration:** delay merging keys that are still being queried.

## 9.7 Threats to validity

- The workload is synthetic, with one seed and one key layout.
- The indexes run single-threaded and in memory: no concurrency, no disk, no database engine.
- The runs were inside Docker on WSL2 on a laptop. Absolute numbers vary between runs: the B+ tree's P1 throughput was 1.89 million in an earlier run and 1.53 million in this one. Compare configurations within a single run.
- The libraries were used with default settings.


# 10. Conclusion and Future Work

## 10.1 Conclusion

PharmaTrace meets all of its objectives.

**The database.** A normalised PostgreSQL schema, of 20 tables in 3NF (also BCNF), enforces the cold-chain workflow itself:

- excursions raise incidents automatically and link only the batches whose own limits were breached;
- dispatching and receiving are atomic and safe under concurrency;
- batch decisions follow role-based transition rules;
- an incident closes only when every investigation, corrective action and batch assessment is complete;
- every decision is audited, with who, when, what and why.

**The application.** The web application exposes this through 12 pages and 50 API endpoints. Validation and authorisation are enforced at three layers: browser, API and database.

**Testing.** All 34 planned test cases pass, each with the system's actual response recorded as evidence. All 68 automated tests pass, and the complete scenario runs end to end through the browser.

**The Innovative Experiment.** A learned index (ALEX) is about twice as fast as a B+ tree for reads on this workload, but pays for sudden distribution shifts with insert pauses of tens of milliseconds and twice the memory. The proposed ALEX-HB variant buffers hot sensors' inserts:

- it removes those pauses during incidents (worst insert 0.1 ms instead of 37.5 ms);
- it gives the best throughput of all configurations in the combined-shift phase;
- it costs half of ALEX's throughput in the investigation phase, where its deferred migration runs.

Both the gains and the losses are reported as measured.

## 10.2 Limitations

- Sensor readings are simulated; there is no hardware integration.
- Temperature limits and severity thresholds are illustrative, not regulatory values.
- The index benchmark is single-threaded and in-memory, and is not integrated into PostgreSQL.
- The application has been demonstrated on one machine; deployment (HTTPS, a production secret store, backups) is outside the project's scope.

## 10.3 Future work

1. **Index research:** faster bulk migration and query-aware migration for ALEX-HB; a parameter sweep over the window W and threshold H; a literature comparison with XIndex and FINEdex.
2. **In-database indexing:** compare PostgreSQL's B-tree and BRIN indexes on `sensor_reading` at tens of millions of rows using `EXPLAIN (ANALYZE, BUFFERS)`.
3. **Product-specific stability budgets:** allowed cumulative time out of range, instead of simple limits.
4. **Notifications:** e-mail alerts when an incident opens; escalation of overdue corrective actions.
5. **Data import:** CSV and API ingestion from real data loggers, with sensor calibration records.


# 11. References

1. World Health Organization, *Model guidance for the storage and transport of time- and temperature-sensitive pharmaceutical products*, WHO Technical Report Series No. 961, Annex 9, 2011. https://www.who.int/publications/m/item/trs961-annex9-modelguidanceforstoragetransport
2. World Health Organization, *Technical supplements to the Model guidance* (TRS 961 Annex 9 supplements; TRS 992 Annex 5). https://www.who.int/teams/health-product-and-policy-standards/standards-and-specifications/norms-and-standards-for-pharmaceuticals/guidelines/distribution
3. Y. P. Tsang et al., "An Internet of Things (IoT)-based risk monitoring system for managing cold supply chain risks," *Industrial Management & Data Systems*, 2018.
4. J. Liu, "Development of a Risk Assessment and Early Warning System for Pharmaceutical Cold Chain Transportation Based on Big Data," *Procedia Computer Science*, 2024.
5. W. Wu et al., "Internet of Everything and Digital Twin enabled Service Platform for Cold Chain Logistics," *Journal of Industrial Information Integration*, 2023.
6. T. Kraska, A. Beutel, E. H. Chi, J. Dean and N. Polyzotis, "The Case for Learned Index Structures," *Proc. ACM SIGMOD*, 2018.
7. J. Ding et al., "ALEX: An Updatable Adaptive Learned Index," *Proc. ACM SIGMOD*, 2020, pp. 969–984. https://www.microsoft.com/en-us/research/publication/msr-alex-techreport/
8. R. Marcus et al., "Benchmarking Learned Indexes," *Proc. VLDB Endowment*, 2020.
9. Z. Sun et al., "Learned Index: A Comprehensive Experimental Evaluation," *Proc. VLDB Endowment*, 2023.
10. R. Elmasri and S. B. Navathe, *Fundamentals of Database Systems*, 7th ed., Pearson, 2016.
11. A. Silberschatz, H. F. Korth and S. Sudarshan, *Database System Concepts*, 7th ed., McGraw-Hill, 2019.
12. The PostgreSQL Global Development Group, *PostgreSQL 18 Documentation*. https://www.postgresql.org/docs/18/
13. R. Bayer and E. McCreight, "Organization and maintenance of large ordered indexes," *Acta Informatica*, 1972.
14. D. Comer, "The Ubiquitous B-Tree," *ACM Computing Surveys*, 1979.
15. tlx: a collection of C++ data structures and algorithms (`tlx::btree_map`). https://github.com/tlx/tlx
16. Microsoft Research, ALEX source code. https://github.com/microsoft/ALEX


# Appendix A. Installation and User Guide

**Requirements:**

- Windows 10/11 with PostgreSQL 18 installed as a service;
- Python 3.12 with uv;
- Node.js 22;
- Docker, only for the benchmark.

**First run:**

1. Copy `.env.example` to `.env`, and set `PG_ADMIN_PASSWORD` to the local PostgreSQL `postgres` password.
2. Double-click **`run.bat`**. On the first run it:
   - installs the backend and frontend dependencies;
   - builds the `pharmatrace` database with demonstration data;
   - starts the API (port 8000) and the web application (port 5173) in two windows;
   - opens the browser at http://localhost:5173.
3. **`run.bat reset`** rebuilds the database with fresh demonstration data. Do this shortly before a demonstration, because the data's times are relative to when it was loaded.
4. **`stop.bat`** stops the API and the web application. The database service keeps running.

**Demonstration accounts:**

| Role | Email | Password |
|---|---|---|
| Administrator | admin@pharmatrace.local | admin123 |
| Operator | operator@pharmatrace.local | operator123 |
| Investigator | investigator@pharmatrace.local | investigator123 |
| Investigator | investigator2@pharmatrace.local | investigator2123 |
| Quality manager | qm@pharmatrace.local | qm123 |

**Manual commands** (for developers):

```
cd backend
set UV_PROJECT_ENVIRONMENT=.venv
uv sync
uv run python -m scripts.reset_db          # build and seed the database
uv run uvicorn app.main:app --port 8000    # API; interactive docs at /docs
uv run pytest                              # 68 automated tests
uv run python -m scripts.evidence          # TC01–TC34 evidence run
cd ..\frontend
npm install
npm run dev                                # web app at http://localhost:5173
```

**Using the system:**

1. **Shipment lifecycle (operator).** Shipments → New shipment, with origin, destination, vehicle, arrival, sensor and batches. Then open the shipment and press Dispatch, and later Confirm arrival.
2. **Simulate a failure (administrator).** Dashboard → choose an in-transit shipment → Simulate failure.
3. **Investigate (quality manager, then investigator).** On the incident page:
   - the quality manager assigns an investigator;
   - the investigator assesses each batch, records a decision (for example, on hold), adds corrective actions and completes the investigation.
4. **Resolve.** The quality manager marks the incident resolved, records release or quarantine decisions, then closes it once every action is complete.

# Appendix B. API Reference (50 endpoints)

All endpoints are under `/api`. Every endpoint except login and health requires a `Bearer` token. Roles: Op = operator, Inv = investigator, QM = quality manager, Adm = administrator.

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | /auth/login | Log in (form: username, password) and receive a JWT | Public |
| GET | /auth/me | Current user | Any |
| GET | /health | Liveness check | Public |
| GET, POST | /products | List / register products | Any / Op, QM, Adm |
| PUT | /products/{id} | Update a product | Op, QM, Adm |
| GET, POST | /batches | List and search / register a batch (with intake movement) | Any / Op, QM, Adm |
| GET | /batches/{id}/trace | Stock, movements, shipments, incidents, decision history | Any |
| POST | /batches/{id}/status | Record a batch decision with a reason | Inv, QM (plus the database rule) |
| GET | /batch-transitions | Allowed transitions per role | Any |
| GET, POST | /facilities | List / add facilities (with phone numbers) | Any / Op, QM, Adm |
| GET, POST | /vehicles | List / add vehicles | Any / Op, QM, Adm |
| PATCH | /vehicles/{id} | Change refrigeration status | Op, QM, Adm |
| GET, POST | /sensors | List / register sensors | Any / Op, QM, Adm |
| PATCH | /sensors/{id} | Change installation status | Op, QM, Adm |
| POST | /sensor-assignments | Attach a sensor to a shipment or facility | Op, QM, Adm |
| POST | /sensor-assignments/{id}/end | Detach a sensor | Op, QM, Adm |
| GET | /staff | List staff | Any |
| POST | /staff | Create an account | Adm |
| PATCH | /staff/{id} | Change role, status or password | Adm |
| GET, POST | /shipments | List / create (with lines and sensor) | Any / Op, QM, Adm |
| GET | /shipments/{id} | Detail: lines, limits, sensors, checkpoints, timeline, incidents | Any |
| POST | /shipments/{id}/batches | Add a line | Op, QM, Adm |
| DELETE | /shipments/{id}/batches/{batch} | Remove a line | Op, QM, Adm |
| POST | /shipments/{id}/dispatch | `dispatch_shipment()` | Op, Adm |
| POST | /shipments/{id}/receive | `receive_shipment()` | Op, Adm |
| POST | /shipments/{id}/cancel | Cancel a planned shipment | Op, Adm |
| POST | /shipments/{id}/checkpoints | Record a checkpoint | Op, Adm |
| POST | /readings | Ingest readings (idempotent; returns counts) | Op, Adm |
| GET | /readings | Query by sensor, shipment, time, quality, out of limits | Any |
| GET, POST | /incidents | List / report a manual incident | Any / Op, Inv, QM |
| GET | /incidents/{id} | Full incident detail | Any |
| POST | /incidents/{id}/status | Change status with a reason | Inv, QM (plus the database rules) |
| POST | /incidents/{id}/investigations | Assign an investigator | QM |
| PATCH | /investigations/{id} | Findings and status | Assignee, QM |
| PATCH | /incidents/{id}/batches/{batch} | Assess a batch | Inv, QM |
| POST | /investigations/{id}/actions | Add a corrective action | Inv, QM |
| PATCH | /actions/{id} | Update an action's status | Assignee, Inv, QM |
| GET | /dashboard | Counters, active shipments, recent incidents | Any |
| GET | /reports, /reports/{key} | Report list / one report (whitelisted views) | Any |
| GET | /audit | Audit log | QM, Adm |
| POST | /admin/simulate-excursion | Start a simulated refrigeration failure | Adm |
| POST | /admin/backfill | Fill normal readings up to now | Adm, Op |

A row with two methods (for example "GET, POST") or two paths covers two endpoints, so the 42 rows above add up to 50 endpoints.

# Appendix C. Test Evidence in Full

Generated by `backend/scripts/evidence.py`; raw data is in `docs/final-report/evidence/test_evidence.json`.

**TC01: Register a valid product** (Product)

- *Input / action:* INSERT product 'Vaccine X', vaccine, 2.00-8.00 °C
- *Expected:* Product saved; new product_id returned
- *Actual (system output):* `Saved: product_id=4`
- *Status:* **Pass**

**TC02: Invalid temperature range rejected** (Product)

- *Input / action:* INSERT product with min_temp 8, max_temp 2
- *Expected:* Rejected by CHECK (min_temp < max_temp)
- *Actual (system output):* `CheckViolation: new row for relation "product" violates check constraint "product_temp_range" [constraint product_temp_range]`
- *Status:* **Pass**

**TC03: Duplicate batch number rejected** (Batch)

- *Input / action:* INSERT a second batch with number B1
- *Expected:* Second insert rejected (UNIQUE)
- *Actual (system output):* `UniqueViolation: duplicate key value violates unique constraint "batch_batch_number_key" [constraint batch_batch_number_key]`
- *Status:* **Pass**

**TC04: Expiry before manufacture rejected** (Batch)

- *Input / action:* INSERT batch mfg 2026-05-01, expiry 2026-04-01
- *Expected:* Rejected by CHECK (expiry_date > manufacturing_date)
- *Actual (system output):* `CheckViolation: new row for relation "batch" violates check constraint "batch_dates" [constraint batch_dates]`
- *Status:* **Pass**

**TC05: Quantity boundary** (Batch)

- *Input / action:* INSERT batch with initial_quantity 0, then 1
- *Expected:* 0 rejected; 1 accepted
- *Actual (system output):* Quantity 0 -> CheckViolation: new row for relation "batch" violates check constraint "batch_initial_quantity_check" [constraint batch_initial_quantity_check]. Quantity 1 -> saved (batch_id=7)
- *Status:* **Pass**

**TC06: Product with batches cannot be deleted** (Product)

- *Input / action:* DELETE product 'Vaccine A' (has batches)
- *Expected:* Rejected by foreign key (ON DELETE RESTRICT)
- *Actual (system output):* RestrictViolation: update or delete on table "product" violates RESTRICT setting of foreign key constraint "batch_product_id_fkey" on table "batch" [constraint batch_product_id_fkey]
- *Status:* **Pass**

**TC07: Shipment with nonexistent vehicle rejected** (Shipment)

- *Input / action:* INSERT shipment with vehicle_id 999
- *Expected:* Rejected by foreign key
- *Actual (system output):* ForeignKeyViolation: insert or update on table "shipment" violates foreign key constraint "shipment_vehicle_id_fkey" [constraint shipment_vehicle_id_fkey]
- *Status:* **Pass**

**TC08: Same origin and destination rejected** (Shipment)

- *Input / action:* INSERT shipment Warehouse -> Warehouse
- *Expected:* Rejected by CHECK (origin <> destination)
- *Actual (system output):* `CheckViolation: new row for relation "shipment" violates check constraint "shipment_route" [constraint shipment_route]`
- *Status:* **Pass**

**TC09: Add batch to shipment** (Shipment)

- *Input / action:* INSERT shipment_batch (shipment, B1, 1000)
- *Expected:* Row saved in SHIPMENT_BATCH
- *Actual (system output):* `Saved: shipment 1 carries B1 x 1000`
- *Status:* **Pass**

**TC10: Same batch twice in one shipment rejected** (Shipment)

- *Input / action:* INSERT shipment_batch B1 again for the same shipment
- *Expected:* Rejected (composite primary key)
- *Actual (system output):* `UniqueViolation: duplicate key value violates unique constraint "shipment_batch_pkey" [constraint shipment_batch_pkey]`
- *Status:* **Pass**

**TC11: Dispatch a shipment** (Transaction)

- *Input / action:* SELECT dispatch_shipment() for B1 x400 + B2 x100 with sensor attached
- *Expected:* Status in_transit; dispatch movements and departure checkpoint recorded; stock reduced
- *Actual (system output):* `status=in_transit; dispatched movements=2; checkpoint=departure; B1 stock at origin 1000 -> 600`
- *Status:* **Pass**

**TC12: Partial failure rolls back the whole dispatch** (Transaction)

- *Input / action:* dispatch_shipment() with B1 x100 (in stock) and B2 x9999 (only 500 in stock)
- *Expected:* Error raised; no movement kept for B1 or B2; status stays planned
- *Actual (system output):* RaiseException: Insufficient stock of batch B2: 500 at origin, 9999 requested. Afterwards: movements for this shipment=0, status=planned, B1 stock=1000 (unchanged)
- *Status:* **Pass**

**TC13: Expired or quarantined batch cannot be dispatched** (Transaction)

- *Input / action:* dispatch_shipment() with an expired batch; then with a quarantined batch
- *Expected:* Dispatch rejected with a message
- *Actual (system output):* Expired: RaiseException: Batch BEXP expired on 2026-11-07; it cannot be dispatched. Quarantined: RaiseException: Batch B1 is quarantined; it cannot be dispatched
- *Status:* **Pass**

**TC14: Two concurrent dispatches cannot oversell stock** (Concurrency)

- *Input / action:* Two sessions each dispatch 800 of the 1,000 units of B1 at the same time
- *Expected:* One commits, the other fails; stock never negative
- *Actual (system output):* Session 1 committed. Session 2 waited for the row lock (waiting=True), then: RaiseException: Insufficient stock of batch B1: 200 at origin, 800 requested. Final B1 stock at origin = 200
- *Status:* **Pass**

**TC15: Receive a shipment** (Transaction)

- *Input / action:* dispatch_shipment() then receive_shipment() for B1 x300
- *Expected:* Status delivered; stock moved to destination; sensor assignment closed
- *Actual (system output):* `status=delivered; B1 stock at destination=300; open sensor assignments=0`
- *Status:* **Pass**

**TC16: Overlapping sensor assignment rejected** (Monitoring)

- *Input / action:* Assign sensor S1 to a second shipment while it is still attached to the first
- *Expected:* Rejected (EXCLUDE constraint)
- *Actual (system output):* `ExclusionViolation: conflicting key value violates exclusion constraint "assignment_no_overlap" [constraint assignment_no_overlap]`
- *Status:* **Pass**

**TC17: Valid reading inside limits** (Monitoring)

- *Input / action:* Reading 5.2 °C from S1 on a dispatched shipment
- *Expected:* Reading saved as valid; no incident
- *Actual (system output):* `reading_id=1 stored, quality=valid; incidents=0`
- *Status:* **Pass**

**TC18: Reading outside limits raises an incident** (Monitoring)

- *Input / action:* Readings 5.2 °C, then 8.6 °C (vaccine limit 8 °C)
- *Expected:* Reading saved; incident created and linked to shipment, reading and batch
- *Actual (system output):* `1 incident: id=1, type=temperature_excursion, shipment=1, source=automatic, status=open, severity=low; breaching reading linked=True`
- *Status:* **Pass**

**TC19: Repeated breach appends to the same incident** (Monitoring)

- *Input / action:* Readings 8.6 °C then 12.5 °C
- *Expected:* Same open incident; severity raised; no new incident
- *Actual (system output):* `incidents=1; severity low -> high; linked readings=2`
- *Status:* **Pass**

**TC20: Duplicate reading rejected** (Monitoring)

- *Input / action:* Same sensor and timestamp inserted twice
- *Expected:* Rejected (UNIQUE sensor_id, recorded_at)
- *Actual (system output):* `UniqueViolation: duplicate key value violates unique constraint "reading_unique_per_sensor" [constraint reading_unique_per_sensor]`
- *Status:* **Pass**

**TC21: Future timestamp stored as invalid** (Monitoring)

- *Input / action:* Reading 20 °C recorded 2 hours in the future
- *Expected:* Stored with quality invalid; no incident
- *Actual (system output):* `reading_id=1 stored, quality=invalid; incidents=0`
- *Status:* **Pass**

**TC22: Missing readings appear in the data-quality report** (Monitoring)

- *Input / action:* Readings at -45, -40, -35, -5, 0 min (5-minute sensor) -> a 30-minute hole
- *Expected:* Gap shown in the sensor quality report
- *Actual (system output):* `v_report_sensor_quality for S1: gaps=1, longest_gap_minutes=30`
- *Status:* **Pass**

**TC23: Original reading values are protected** (Monitoring)

- *Input / action:* UPDATE the temperature of a stored reading; DELETE it; UPDATE only its quality flag
- *Expected:* Value change and delete rejected by trigger; quality flag change allowed
- *Actual (system output):* UPDATE value -> RaiseException: Original values of reading 1 cannot be changed; only quality_status may be updated. DELETE -> RaiseException: Sensor readings cannot be deleted (reading 1). Quality flag update -> allowed; temperature still 5.00
- *Status:* **Pass**

**TC24: Trace affected batches** (Incident)

- *Input / action:* Reading 10.1 °C on a shipment carrying vaccine (2-8 °C) and syrup (2-25 °C)
- *Expected:* Only the batches whose own limits were breached are linked
- *Actual (system output):* `Linked batches: ['B1'] (B3 syrup, limit 25 °C, correctly not linked)`
- *Status:* **Pass**

**TC25: Login with a wrong password** (Security)

- *Input / action:* POST /api/auth/login with a valid email and a wrong password
- *Expected:* 401 Unauthorized; no token issued
- *Actual (system output):* `Wrong password -> HTTP 401 {'detail': 'Incorrect email or password'}. Correct password -> HTTP 200 with a token`
- *Status:* **Pass**

**TC26: Unauthorised status change rejected (API and database)** (Security)

- *Input / action:* Operator calls POST /api/batches/B1/status 'released'; operator context runs the UPDATE directly in SQL
- *Expected:* Rejected by the API (403) and by the database trigger
- *Actual (system output):* API -> HTTP 403 {'detail': 'Requires role: investigator, quality_manager'}. Direct SQL -> InsufficientPrivilege: Role operator may not change batch B1 from available to on_hold
- *Status:* **Pass**

**TC27: SQL injection attempt** (Security)

- *Input / action:* GET /api/batches?q=' OR 1=1 --
- *Expected:* Treated as plain text; no extra rows
- *Actual (system output):* `All batches: 5 rows. Injection string -> HTTP 200, 0 rows (searched literally)`
- *Status:* **Pass**

**TC28: Application role cannot delete readings or write the audit log** (Security)

- *Input / action:* As pharmatrace_app: DELETE FROM sensor_reading; INSERT INTO audit_log
- *Expected:* Permission denied
- *Actual (system output):* DELETE readings -> InsufficientPrivilege: permission denied for table sensor_reading. INSERT audit_log -> InsufficientPrivilege: permission denied for table audit_log
- *Status:* **Pass**

**TC29: Complete an investigation** (Investigation)

- *Input / action:* Mark investigation completed without findings; then with findings
- *Expected:* Rejected without findings; with findings completed_at is recorded
- *Actual (system output):* Without findings -> CheckViolation: new row for relation "investigation" violates check constraint "investigation_findings" [constraint investigation_findings]. With findings -> completed (completed_at recorded=True)
- *Status:* **Pass**

**TC30: Closing an incident too early is refused** (Investigation)

- *Input / action:* Resolve the incident, then close it while a corrective action is pending (and batches unassessed)
- *Expected:* Rejected with the reason shown
- *Actual (system output):* With a pending action -> RaiseException: Incident 1 has corrective actions that are not finished. With the action done but batches unassessed -> RaiseException: Incident 1 has affected batches that are not assessed
- *Status:* **Pass**

**TC31: Close a fully resolved incident** (Investigation)

- *Input / action:* All work done; investigator tries to close; quality manager closes
- *Expected:* Only the QM can close; status closed; audit entry
- *Actual (system output):* Investigator -> InsufficientPrivilege: Only a quality manager can close an incident. Quality manager -> closed. Latest audit entry: incident_status=closed, changed_by=Quality Manager
- *Status:* **Pass**

**TC32: Dashboard counts match base tables** (Reports)

- *Input / action:* Compare v_dashboard with direct COUNT queries
- *Expected:* Every dashboard number equals the matching SQL count
- *Actual (system output):* `v_dashboard (active shipments, open incidents, batches under investigation) = (1, 1, 2); direct counts = (1, 1, 2)`
- *Status:* **Pass**

**TC33: Incident report totals match** (Reports)

- *Input / action:* SUM of v_report_incidents_by_type_severity vs COUNT(*) FROM incident
- *Expected:* Report total equals the table count
- *Actual (system output):* `Report total=1; COUNT(*) FROM incident=1`
- *Status:* **Pass**

**TC34: Required-field and range validation** (Forms)

- *Input / action:* POST /api/shipments without destination; POST /api/products with min 8 > max 2
- *Expected:* 422 with a message naming the problem; nothing saved
- *Actual (system output):* Shipment -> HTTP 422, missing fields ['destination_facility_id', 'expected_arrival']. Product -> HTTP 422, 'Value error, Minimum temperature must be below maximum temperature'. Shipments saved: 0
- *Status:* **Pass**


# Appendix D. Key SQL Listings

These listings are copied from the source files at build time.

### D.1 `dispatch_shipment` (atomic, concurrency-safe dispatch), from `db/03_functions.sql`

```sql
CREATE FUNCTION dispatch_shipment(p_shipment_id integer, p_at timestamptz DEFAULT now())
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    s        shipment%ROWTYPE;
    v_origin facility.facility_name%TYPE;
    v_fridge vehicle.refrigeration_status%TYPE;
    line     record;
    v_stock  integer;
BEGIN
    SELECT * INTO s FROM shipment WHERE shipment_id = p_shipment_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Shipment % does not exist', p_shipment_id USING ERRCODE = 'no_data_found';
    END IF;
    IF s.shipment_status <> 'planned' THEN
        RAISE EXCEPTION 'Shipment % is %; only planned shipments can be dispatched', p_shipment_id, s.shipment_status;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM shipment_batch WHERE shipment_id = p_shipment_id) THEN
        RAISE EXCEPTION 'Shipment % has no batches', p_shipment_id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM sensor_assignment WHERE shipment_id = p_shipment_id AND unassigned_at IS NULL) THEN
        RAISE EXCEPTION 'Shipment % has no active monitoring sensor', p_shipment_id;
    END IF;
    SELECT refrigeration_status INTO v_fridge FROM vehicle WHERE vehicle_id = s.vehicle_id;
    IF v_fridge = 'faulty' THEN
        RAISE EXCEPTION 'Vehicle refrigeration is faulty; shipment % cannot be dispatched', p_shipment_id;
    END IF;

    -- Lock batch rows in a fixed order so two concurrent dispatches cannot deadlock or both
    -- consume the same stock: the second waits, then sees the first one's movements.
    PERFORM 1 FROM batch b JOIN shipment_batch sb ON sb.batch_id = b.batch_id
    WHERE sb.shipment_id = p_shipment_id ORDER BY b.batch_id FOR UPDATE OF b;

    FOR line IN
        SELECT sb.batch_id, sb.quantity_shipped, b.batch_number, b.batch_status, b.expiry_date
        FROM shipment_batch sb JOIN batch b ON b.batch_id = sb.batch_id
        WHERE sb.shipment_id = p_shipment_id ORDER BY sb.batch_id
    LOOP
        IF line.batch_status NOT IN ('available', 'released') THEN
            RAISE EXCEPTION 'Batch % is %; it cannot be dispatched', line.batch_number, line.batch_status;
        END IF;
        IF line.expiry_date <= p_at::date THEN
            RAISE EXCEPTION 'Batch % expired on %; it cannot be dispatched', line.batch_number, line.expiry_date;
        END IF;
        v_stock := batch_stock_at(line.batch_id, s.origin_facility_id, p_at);
        IF v_stock < line.quantity_shipped THEN
            RAISE EXCEPTION 'Insufficient stock of batch %: % at origin, % requested',
                line.batch_number, v_stock, line.quantity_shipped;
        END IF;
        INSERT INTO batch_movement (batch_id, facility_id, shipment_id, movement_type, movement_time, quantity_moved)
        VALUES (line.batch_id, s.origin_facility_id, p_shipment_id, 'dispatched', p_at, line.quantity_shipped);
    END LOOP;

    SELECT facility_name INTO v_origin FROM facility WHERE facility_id = s.origin_facility_id;
    INSERT INTO shipment_checkpoint (shipment_id, checkpoint_no, checkpoint_time, event_type, location_description)
    SELECT p_shipment_id, COALESCE(MAX(checkpoint_no), 0) + 1, p_at, 'departure', 'Departed ' || v_origin
    FROM shipment_checkpoint WHERE shipment_id = p_shipment_id;

    UPDATE shipment SET shipment_status = 'in_transit', dispatch_time = p_at WHERE shipment_id = p_shipment_id;
END;
$$;
```

### D.2 `trg_reading_evaluate` (excursion detection), from `db/04_triggers.sql`

```sql
CREATE FUNCTION trg_reading_evaluate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_ship      integer;
    v_fac       integer;
    t_batches   integer[] := '{}';
    t_dev       numeric := 0;
    h_batches   integer[] := '{}';
    h_dev       numeric := 0;
    h_watched   boolean := false;
    r           record;
    d           numeric;
BEGIN
    IF NEW.quality_status <> 'valid' THEN
        RETURN NULL;
    END IF;
    SELECT shipment_id, facility_id INTO v_ship, v_fac FROM sensor_assignment
    WHERE sensor_id = NEW.sensor_id AND assigned_at <= NEW.recorded_at
      AND (unassigned_at IS NULL OR NEW.recorded_at < unassigned_at);
    IF NOT FOUND THEN
        RETURN NULL;   -- reading from an unassigned sensor: stored, but nothing to evaluate
    END IF;

    FOR r IN
        SELECT t.batch_id, p.min_temp, p.max_temp, p.min_humidity, p.max_humidity
        FROM batches_at_target(v_ship, v_fac, NEW.recorded_at) t
        JOIN batch b ON b.batch_id = t.batch_id
        JOIN product p ON p.product_id = b.product_id
    LOOP
        IF NEW.temperature IS NOT NULL THEN
            d := GREATEST(NEW.temperature - r.max_temp, r.min_temp - NEW.temperature, 0);
            IF d > 0 THEN
                t_batches := t_batches || r.batch_id;
                t_dev := GREATEST(t_dev, d);
            END IF;
        END IF;
        IF NEW.humidity IS NOT NULL AND r.min_humidity IS NOT NULL THEN
            h_watched := true;
            d := GREATEST(NEW.humidity - r.max_humidity, r.min_humidity - NEW.humidity, 0);
            IF d > 0 THEN
                h_batches := h_batches || r.batch_id;
                h_dev := GREATEST(h_dev, d / 5);   -- 5 % RH counted like 1 °C for severity
            END IF;
        END IF;
    END LOOP;

    IF NEW.temperature IS NOT NULL THEN
        IF cardinality(t_batches) > 0 THEN
            PERFORM record_excursion('temperature_excursion', v_ship, v_fac, NEW, t_dev, t_batches,
                format('%s °C, %s °C outside limit', NEW.temperature, t_dev));
        ELSE
            PERFORM end_excursion('temperature_excursion', v_ship, v_fac, NEW);
        END IF;
    END IF;
    IF h_watched THEN
        IF cardinality(h_batches) > 0 THEN
            PERFORM record_excursion('humidity_excursion', v_ship, v_fac, NEW, h_dev, h_batches,
                format('%s %% RH outside limit', NEW.humidity));
        ELSE
            PERFORM end_excursion('humidity_excursion', v_ship, v_fac, NEW);
        END IF;
    END IF;
    RETURN NULL;
END;
$$;
```

### D.3 `record_excursion` (open or update an incident), from `db/04_triggers.sql`

```sql
CREATE FUNCTION record_excursion(p_type varchar, p_shipment integer, p_facility integer, p_reading sensor_reading,
                                 p_deviation numeric, p_batches integer[], p_note text)
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE
    v_id       integer;
    v_severity varchar;
    v_new_sev  varchar := severity_for_deviation(p_deviation);
BEGIN
    -- serialise detection per target so two readings cannot both create an incident
    PERFORM pg_advisory_xact_lock(hashtext('incident:' || p_type || ':' || COALESCE('s' || p_shipment, 'f' || p_facility)));

    SELECT incident_id, severity INTO v_id, v_severity FROM incident
    WHERE incident_type = p_type AND incident_status IN ('open', 'investigating')
      AND ((p_shipment IS NOT NULL AND shipment_id = p_shipment) OR (p_facility IS NOT NULL AND facility_id = p_facility))
    FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO incident (incident_type, severity, detection_source, shipment_id, facility_id,
                              detected_at, start_time, description)
        VALUES (p_type, v_new_sev, 'automatic', p_shipment, p_facility, p_reading.ingested_at, p_reading.recorded_at,
                format('Automatic: %s detected by sensor %s at %s', replace(p_type, '_', ' '),
                       p_reading.sensor_id, to_char(p_reading.recorded_at, 'YYYY-MM-DD HH24:MI TZ')))
        RETURNING incident_id INTO v_id;
    ELSE
        UPDATE incident
        SET severity = CASE WHEN severity_rank(v_new_sev) > severity_rank(severity) THEN v_new_sev ELSE severity END,
            end_time = NULL
        WHERE incident_id = v_id;
    END IF;

    INSERT INTO incident_reading (incident_id, reading_id, relevance_note)
    VALUES (v_id, p_reading.reading_id, p_note) ON CONFLICT DO NOTHING;
    INSERT INTO incident_batch (incident_id, batch_id)
    SELECT v_id, unnest(p_batches) ON CONFLICT DO NOTHING;
    RETURN v_id;
END;
$$;
```

### D.4 `trg_incident_lifecycle` (closing rules), from `db/04_triggers.sql`

```sql
CREATE FUNCTION trg_incident_lifecycle() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.incident_status IS NOT DISTINCT FROM OLD.incident_status THEN
        RETURN NEW;
    END IF;
    IF (OLD.incident_status, NEW.incident_status) NOT IN
       (('open', 'investigating'), ('investigating', 'resolved'), ('resolved', 'closed'), ('resolved', 'investigating')) THEN
        RAISE EXCEPTION 'Incident % cannot move from % to %', OLD.incident_id, OLD.incident_status, NEW.incident_status;
    END IF;

    IF NEW.incident_status = 'resolved' THEN
        IF NOT EXISTS (SELECT 1 FROM investigation WHERE incident_id = NEW.incident_id) THEN
            RAISE EXCEPTION 'Incident % has no investigation', NEW.incident_id;
        END IF;
        IF EXISTS (SELECT 1 FROM investigation WHERE incident_id = NEW.incident_id
                   AND investigation_status <> 'completed') THEN
            RAISE EXCEPTION 'Incident % still has an investigation that is not completed', NEW.incident_id;
        END IF;
    END IF;

    IF NEW.incident_status = 'closed' THEN
        IF current_staff_role() IS DISTINCT FROM 'quality_manager' THEN
            RAISE EXCEPTION 'Only a quality manager can close an incident' USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF EXISTS (SELECT 1 FROM corrective_action ca JOIN investigation iv ON iv.investigation_id = ca.investigation_id
                   WHERE iv.incident_id = NEW.incident_id AND ca.action_status IN ('pending', 'in_progress')) THEN
            RAISE EXCEPTION 'Incident % has corrective actions that are not finished', NEW.incident_id;
        END IF;
        IF EXISTS (SELECT 1 FROM incident_batch WHERE incident_id = NEW.incident_id
                   AND assessment_status <> 'assessed') THEN
            RAISE EXCEPTION 'Incident % has affected batches that are not assessed', NEW.incident_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
```

### D.5 `trg_batch_status_check` (role-based decisions), from `db/04_triggers.sql`

```sql
CREATE FUNCTION trg_batch_status_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_role varchar := current_staff_role();
BEGIN
    IF NEW.batch_status IS DISTINCT FROM OLD.batch_status THEN
        IF v_role IS NULL THEN
            RAISE EXCEPTION 'Batch status changes require an authenticated staff member';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM batch_status_transition
                       WHERE from_status = OLD.batch_status AND to_status = NEW.batch_status AND role = v_role) THEN
            RAISE EXCEPTION 'Role % may not change batch % from % to %',
                v_role, OLD.batch_number, OLD.batch_status, NEW.batch_status
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
```

### D.6 `v_dashboard`, from `db/05_views.sql`

```sql
CREATE VIEW v_dashboard AS
SELECT
    (SELECT COUNT(*) FROM shipment WHERE shipment_status = 'in_transit')                       AS active_shipments,
    (SELECT COUNT(*) FROM incident WHERE incident_status IN ('open', 'investigating'))         AS open_incidents,
    (SELECT COUNT(DISTINCT ib.batch_id) FROM incident_batch ib JOIN incident i ON i.incident_id = ib.incident_id
      WHERE i.incident_status IN ('open', 'investigating', 'resolved'))                        AS batches_under_investigation,
    (SELECT COUNT(*) FROM corrective_action
      WHERE action_status IN ('pending', 'in_progress') AND due_date < CURRENT_DATE)           AS overdue_actions,
    (SELECT COUNT(*) FROM incident WHERE incident_type IN ('temperature_excursion', 'humidity_excursion')
      AND detected_at >= now() - interval '7 days')                                            AS excursions_last_7_days,
    (SELECT COUNT(*) FROM shipment WHERE shipment_status = 'in_transit' AND expected_arrival < now())
                                                                                               AS overdue_arrivals,
    (SELECT COUNT(*) FROM batch WHERE batch_status IN ('on_hold', 'quarantined'))              AS batches_on_hold;
```

# Appendix E. Project Structure

```
DBMSEL/
  db/                 00_extensions … 06_grants.sql, queries/demo.sql
  backend/            app/ (FastAPI), scripts/ (reset_db, seed, evidence, test_report), tests/ (68 tests)
  frontend/           src/ (React + TypeScript: 12 pages)
  benchmark/          workload/gen.py, src/bench.cpp, Dockerfile, run_all.sh, analysis/analyze.py,
                      results/ (4 configurations), results_baseline/, results_m1/
  tools/e2e/          check.mjs, demo.mjs, report_shots.mjs (browser tests)
  docs/               lab-manual/ (diagrams), final-report/ (this report), benchmark-report.md,
                      experiment-phase4.md, test-report.md
  run.bat, stop.bat   launchers
  README.md, HANDOFF.md, CLAUDE.md, idea.md
```

# Appendix F. Demonstration Script

1. **Normal operation.** Log in as the administrator and show the dashboard counters, which are SQL views.
2. **Failure.** In the simulator panel, choose SH004 and press Simulate failure. Readings arrive every 2.5 s.
3. **Incident.** INC0003 appears, raised by the database. Show the chart, the exposure, the peak and the three breached batches.
4. **Trace.** Open a batch: chain of custody, stock per facility, incidents.
5. **Investigate.**
   - The quality manager assigns the investigator.
   - The investigator assesses the batches, puts one on hold, adds an action and completes the investigation.
6. **Resolve.**
   - Close the incident too early: the database refuses.
   - The operator completes the action.
   - The quality manager releases the batch and closes the incident. Show the history.
7. **Database.** Run `db/queries/demo.sql` in psql (listing below).
8. **Research.** Show Chapter 9's figures.

```sql
-- PharmaTrace: queries to run live in the demo (Scene 7). Run in psql connected to the pharmatrace database.
--   psql -h localhost -U postgres -d pharmatrace -f db/queries/demo.sql      (or paste section by section)

-- 1. Join across five tables: which batches are on which shipment, from where to where
SELECT 'SH' || lpad(s.shipment_id::text, 3, '0') AS shipment, o.facility_name AS origin, d.facility_name AS destination,
       b.batch_number, p.product_name, sb.quantity_shipped, s.shipment_status
FROM shipment s
JOIN facility o ON o.facility_id = s.origin_facility_id
JOIN facility d ON d.facility_id = s.destination_facility_id
JOIN shipment_batch sb ON sb.shipment_id = s.shipment_id
JOIN batch b ON b.batch_id = sb.batch_id
JOIN product p ON p.product_id = b.product_id
ORDER BY s.shipment_id, b.batch_number;

-- 2. Trace an incident: affected batches and where each batch is now (derived from movement history)
SELECT i.incident_code, b.batch_number, ib.assessment_status, st.facility_name, st.on_hand
FROM v_incident_summary i
JOIN incident_batch ib ON ib.incident_id = i.incident_id
JOIN batch b ON b.batch_id = ib.batch_id
LEFT JOIN v_batch_stock st ON st.batch_id = b.batch_id
ORDER BY i.incident_id, b.batch_number;

-- 3. Aggregation with HAVING: vehicles involved in more than one incident
SELECT * FROM v_report_vehicle_repeat_incidents;

-- 4. Correlated subquery: batches whose current stock is below 50 % of the initial quantity
SELECT b.batch_number, b.initial_quantity,
       (SELECT COALESCE(SUM(on_hand), 0) FROM v_batch_stock s WHERE s.batch_id = b.batch_id) AS on_hand
FROM batch b
WHERE (SELECT COALESCE(SUM(on_hand), 0) FROM v_batch_stock s WHERE s.batch_id = b.batch_id) < b.initial_quantity / 2;

-- 5. Window function: gaps in a sensor's readings longer than twice its expected interval
SELECT serial_number, recorded_at, gap
FROM (SELECT s.serial_number, r.recorded_at, s.expected_interval_s,
             r.recorded_at - LAG(r.recorded_at) OVER (PARTITION BY r.sensor_id ORDER BY r.recorded_at) AS gap
      FROM sensor_reading r JOIN sensor s USING (sensor_id)) g
WHERE gap > make_interval(secs => 2 * expected_interval_s)
ORDER BY gap DESC LIMIT 10;

-- 6. Constraint demos (each statement fails with a clear error)
INSERT INTO product (product_name, product_type, min_temp, max_temp) VALUES ('Bad', 'vaccine', 8, 2);     -- CHECK
INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
VALUES (999, 1, 2, now() + interval '1 day');                                                             -- FOREIGN KEY
UPDATE sensor_reading SET temperature = 4 WHERE reading_id = 1;                                            -- trigger: readings are immutable

-- 7. Transaction rollback: dispatch fails on the second batch, so the first batch's movement is undone too
BEGIN;
INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
VALUES (1, 1, 2, now() + interval '1 day') RETURNING shipment_id \gset
INSERT INTO shipment_batch VALUES (:shipment_id, 9, 100), (:shipment_id, 10, 99999);   -- B009 fine, B010 short
INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (8, :shipment_id, now());
SELECT dispatch_shipment(:shipment_id);          -- ERROR: Insufficient stock of batch B010
ROLLBACK;
SELECT COUNT(*) AS leftover_movements FROM batch_movement WHERE shipment_id = :shipment_id;   -- 0

-- 8. Role rule enforced inside the database, not only in the app
BEGIN;
SELECT set_config('app.current_staff_id', '2', true);   -- staff 2 = operator
UPDATE batch SET batch_status = 'released' WHERE batch_number = 'B005';   -- ERROR: Role operator may not change batch
ROLLBACK;

-- 9. Index use: the per-sensor lookup uses the UNIQUE (sensor_id, recorded_at) B-tree
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM sensor_reading WHERE sensor_id = 1 AND recorded_at BETWEEN now() - interval '1 day' AND now();
```
