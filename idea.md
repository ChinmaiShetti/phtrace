1. Project overview
Proposed name: PharmaTrace

Full title: PharmaTrace: Pharmaceutical Cold-Chain Integrity, Traceability and Incident Management System

One-line description

A database-driven application that tracks temperature-sensitive pharmaceutical products throughout their supply chain, records environmental conditions, identifies potential cold-chain incidents, traces affected medicine batches, and manages investigations and corrective actions.

The problem we're solving

Imagine a pharmaceutical company transporting 10,000 vaccine doses from a central warehouse to several hospitals.

The shipment passes through:

A pharmaceutical warehouse.
A refrigerated vehicle.
A regional distribution centre.
Several hospitals or clinics.

Throughout this journey, temperature sensors record environmental readings.

Now imagine the refrigeration system fails during transportation.

The temperature rises beyond the permitted range.

The company needs to determine:

Which shipment experienced the problem?
Which medicine batches were inside it?
How long were those batches exposed?
Which other shipments might be affected by the same incident?
Where have the affected batches been delivered?
Which batches require investigation?
Who is responsible for investigating the incident?
What corrective action was taken?
Has the incident been resolved and documented?

Without a properly connected system, information about shipments, batches, readings, deliveries and investigations may be scattered across different records.

PharmaTrace brings these records together in one relational database.

The application supports traceability and investigation. It does not independently determine whether a medicine is safe to use; that decision must follow the applicable pharmaceutical quality procedures and approved product-specific requirements.

2. What exactly are we building?

Think of PharmaTrace as five connected subsystems.

Subsystem	Purpose
Pharmaceutical inventory	Maintain products, batches, expiry dates and quantities
Shipment tracking	Track shipments, vehicles, routes and delivery destinations
Environmental monitoring	Store temperature and humidity readings
Incident management	Record excursions, identify potentially affected batches and track investigations
Corrective-action management	Assign investigations, record decisions and document resolution

These are not five separate projects. They are five parts of a single application backed by a relational database.

Let's understand each one.

Module A: Pharmaceutical product and batch management

The system stores the pharmaceutical products being transported.

For example:

Product ID	Product	Storage requirement
P101	Vaccine A	2–8°C
P102	Medicine B	Product-specific limits
P103	Biologic C	Product-specific limits

These values are illustrative. Actual storage requirements must come from the relevant product's approved specifications.

A product can have multiple batches.

For example:

PRODUCT: Vaccine A
    |
    ├── Batch B001
    ├── Batch B002
    ├── Batch B003
    └── Batch B004

Each batch can have its own:

Batch number.
Manufacturing date.
Expiry date.
Initial quantity.
Current recorded quantity.
Quality status.
Current location.

Why is this important?

Suppose Batch B002 experiences a temperature excursion, but B001, B003 and B004 do not.

The system should allow investigators to trace B002 specifically rather than treating the entire product as one undifferentiated item.

Module B: Shipment and transportation tracking

Every shipment contains one or more pharmaceutical batches.

For example:

Shipment SH001
    |
    ├── Batch B001: 1,000 units
    ├── Batch B002: 2,000 units
    └── Batch B005: 500 units

The shipment records:

Shipment identifier.
Dispatch time.
Expected arrival.
Actual arrival.
Origin and destination.
Assigned vehicle.
Shipment status.

We can also record individual journey checkpoints.

For example:

Time	Shipment	Checkpoint	Status
08:00	SH001	Central warehouse	Dispatched
10:00	SH001	Checkpoint A	In transit
12:30	SH001	Distribution centre	Arrived
14:00	SH001	Regional warehouse	Received

This becomes useful when an investigator needs to reconstruct where a shipment was at the time an incident occurred.

Module C: Environmental monitoring

This module stores measurements collected from sensors attached to storage facilities or shipments.

For example:

Reading ID	Sensor	Time	Temperature
R001	S101	10:00	5.2°C
R002	S101	10:05	5.8°C
R003	S101	10:10	8.6°C
R004	S101	10:15	10.1°C

The database preserves the original readings and their timestamps.

The system can compare the readings against the applicable configured monitoring limits.

We should also store humidity where relevant, sensor health, data quality and missing-reading events.

WHO guidance specifically covers electronic temperature monitoring and monitoring across storage and transportation.

For our student project, we do not need physical sensors initially. We can generate simulated readings at fixed intervals.

This makes the application much easier to implement and test.

Module D: Incident management

This is the heart of the application.

An incident occurs when a monitored condition violates a configured rule or an operator reports a potential problem.

Example:

Incident: INC0042
Shipment: SH001
Type: Temperature excursion
Detected: 10:10 AM
Severity: High
Status: Open

The incident should record:

Incident identifier.
Incident type.
Affected shipment or facility.
Start and end time, if known.
Relevant sensor readings.
Severity.
Detection source.
Investigation status.
Assigned investigator.

The application should also identify the pharmaceutical batches associated with the affected shipment.

However, a temperature excursion does not automatically mean every medicine in that shipment is unusable. Its significance depends on the product, the actual exposure, and the applicable quality procedures.

Module E: Investigation and corrective actions

After an incident is detected, an authorised user investigates it.

The application can support this workflow:

Open the incident.
Inspect the relevant temperature readings.
Identify potentially affected batches.
Check their recorded locations and movements.
Assign an investigator.
Record the investigation findings.
Record the decision made by the responsible quality personnel.
Document corrective action.
Close the incident after the required review.

Possible recorded decisions might include:

Continue monitoring.
Hold the batch pending investigation.
Quarantine the batch.
Release the batch following the required review.
Return or dispose of the product according to the applicable procedure.

These are workflow statuses and recorded decisions, not automatic recommendations from our software.

This is the part that differentiates our application from a basic temperature-monitoring dashboard. It connects environmental data to the affected inventory, its movement through the supply chain, and the subsequent investigation.

3. The complete system workflow

Let's walk through one incident from beginning to end.

Suppose a shipment is transporting three batches of temperature-sensitive medicine.

Step 1: Shipment creation

An operator creates a shipment.

Shipment: SH001
Vehicle: V012
Origin: Central Warehouse
Destination: Regional Distribution Centre
Status: In Transit

The operator associates the relevant batches with the shipment.

Step 2: Readings arrive

The system receives or simulates temperature readings.

10:00 AM → 5.2°C
10:05 AM → 5.8°C
10:10 AM → 8.6°C
10:15 AM → 10.1°C

The monitoring rule detects a possible excursion.

Step 3: Incident creation

The application creates an incident and links it to the shipment and relevant sensor.

The incident is assigned an identifier so that subsequent records can refer to it.

Step 4: Batch tracing

The system queries the database to find the batches associated with the shipment.

It retrieves the recorded quantities and relevant shipment history.

Step 5: Location tracing

The application checks which distribution centre or facility received each batch.

If a batch was subsequently transferred, the system can display its recorded movement history.

Step 6: Investigation

An authorised investigator examines the available readings, exposure period and product information.

The investigator records the findings and required actions.

Step 7: Resolution

The system records the final decision, responsible user, timestamps and corrective actions.

The incident is closed only after the required workflow is completed.

The final record remains available for auditing and reporting.

In one diagram
       PHARMACEUTICAL PRODUCT
                 |
                 v
          PRODUCT BATCH
                 |
                 v
             SHIPMENT
                 |
                 v
         SENSOR READINGS
                 |
                 v
       POSSIBLE EXCURSION
                 |
                 v
         INCIDENT CREATED
                 |
                 v
        TRACE AFFECTED BATCHES
                 |
                 v
       TRACE RECORDED LOCATIONS
                 |
                 v
           INVESTIGATION
                 |
                 v
        CORRECTIVE ACTION
                 |
                 v
          INCIDENT CLOSED

This is the main workflow we should build our demo around.

4. The complete proposed database schema

Now let's discuss the actual DBMS design.

I recommend starting with the following entities. We can expand them later if implementation or faculty requirements demand it.

4.1 Core inventory tables
Table 1: PharmaceuticalProduct

Stores product-level information.

Attribute	Type	Description
product_id	INT, PK	Unique product identifier
product_name	VARCHAR	Product name
product_type	VARCHAR	Vaccine, biologic, medicine, etc.
min_storage_temp	DECIMAL	Applicable lower monitoring limit
max_storage_temp	DECIMAL	Applicable upper monitoring limit
min_storage_humidity	DECIMAL, nullable	Optional lower humidity limit
max_storage_humidity	DECIMAL, nullable	Optional upper humidity limit

These are simplified configured monitoring limits. A production system would need a more sophisticated representation of product-specific storage and excursion rules.

Table 2: Batch

Stores individual pharmaceutical batches.

Attribute	Type	Description
batch_id	INT, PK	Internal batch identifier
product_id	INT, FK	Associated product
batch_number	VARCHAR, UNIQUE	Manufacturer's batch number
manufacturing_date	DATE	Manufacturing date
expiry_date	DATE	Expiry date
initial_quantity	INT	Initial recorded quantity
batch_status	VARCHAR	Available, held, quarantined, released, etc.

Relationship: One product can have many batches.

Table 3: Facility

Stores warehouses, distribution centres, pharmacies and hospitals.

Attribute	Type	Description
facility_id	INT, PK	Unique facility identifier
facility_name	VARCHAR	Facility name
facility_type	VARCHAR	Warehouse, distribution centre, hospital, etc.
address	VARCHAR	Facility address
contact_details	VARCHAR	Contact information
Table 4: BatchLocation

Records the movement or location history of a batch.

Attribute	Type	Description
movement_id	INT, PK	Unique movement identifier
batch_id	INT, FK	Batch being moved
facility_id	INT, FK	Recorded facility
shipment_id	INT, FK, nullable	Shipment associated with the movement
movement_type	VARCHAR	Received, dispatched, transferred, etc.
movement_time	DATETIME	Time of movement
quantity_moved	INT	Quantity involved

This is a movement-history table, not merely a field containing the batch's current location.

That distinction matters because we want to reconstruct the chain of custody during an incident.

4.2 Shipment tables
Table 5: Vehicle
Attribute	Type	Description
vehicle_id	INT, PK	Vehicle identifier
registration_number	VARCHAR, UNIQUE	Vehicle registration
vehicle_type	VARCHAR	Refrigerated van, truck, etc.
refrigeration_status	VARCHAR	Operational status
Table 6: Shipment
Attribute	Type	Description
shipment_id	INT, PK	Unique shipment identifier
vehicle_id	INT, FK	Assigned vehicle
origin_facility_id	INT, FK	Dispatch facility
destination_facility_id	INT, FK	Intended destination
dispatch_time	DATETIME	Dispatch time
expected_arrival	DATETIME	Expected arrival time
actual_arrival	DATETIME, nullable	Actual arrival
shipment_status	VARCHAR	Planned, in transit, delivered, etc.
Table 7: ShipmentBatch

This junction table connects shipments and batches.

Attribute	Type	Description
shipment_id	INT, PK/FK	Shipment
batch_id	INT, PK/FK	Batch
quantity_shipped	INT	Quantity included in shipment

Why do we need a separate table?

Because one shipment can contain multiple batches, and the same batch can be split across multiple shipments.

That is a many-to-many relationship.

The composite primary key (shipment_id, batch_id) prevents the same batch from being recorded twice in the same shipment under this simplified model. If split consignments or multiple line items for the same batch within one shipment must be represented independently, we would add a separate shipment-line identifier.

Table 8: ShipmentCheckpoint

Records important events during transportation.

Attribute	Type	Description
checkpoint_id	INT, PK	Checkpoint identifier
shipment_id	INT, FK	Associated shipment
checkpoint_time	DATETIME	Time of event
facility_id	INT, FK, nullable	Facility, if applicable
location_description	VARCHAR	Checkpoint description
event_type	VARCHAR	Departure, arrival, inspection, etc.

This table helps reconstruct the journey.

4.3 Sensor and monitoring tables
Table 9: Sensor
Attribute	Type	Description
sensor_id	INT, PK	Sensor identifier
sensor_type	VARCHAR	Temperature, humidity, etc.
serial_number	VARCHAR, UNIQUE	Device serial number
installation_status	VARCHAR	Active, inactive, faulty

For a more complete model, we can add sensor assignments to vehicles, shipments or facilities. A separate assignment-history table would be appropriate if sensors move between them.

Table 10: SensorAssignment

Tracks where and when a sensor is deployed.

Attribute	Type	Description
assignment_id	INT, PK	Assignment identifier
sensor_id	INT, FK	Sensor
shipment_id	INT, FK, nullable	Associated shipment
facility_id	INT, FK, nullable	Associated facility
assigned_at	DATETIME	Assignment start
unassigned_at	DATETIME, nullable	Assignment end

We should enforce that an assignment refers to a valid monitored target and that conflicting active assignments are prevented.

Table 11: SensorReading

This is likely to become one of the largest tables.

Attribute	Type	Description
reading_id	BIGINT, PK	Unique reading identifier
sensor_id	INT, FK	Reporting sensor
recorded_at	DATETIME	Measurement time
temperature	DECIMAL, nullable	Recorded temperature
humidity	DECIMAL, nullable	Recorded humidity
quality_status	VARCHAR	Valid, suspicious, invalid, etc.

Each row represents a sensor observation.

Example:

reading_id | sensor_id | recorded_at       | temperature
-----------|-----------|-------------------|------------
1001       | 101       | 10:00:00          | 5.2
1002       | 101       | 10:05:00          | 5.8
1003       | 101       | 10:10:00          | 8.6
1004       | 101       | 10:15:00          | 10.1

We should retain the original measurement and timestamp, including readings later marked invalid. Corrections and annotations should not silently erase the original record.

4.4 Incident-management tables
Table 12: Incident
Attribute	Type	Description
incident_id	INT, PK	Unique incident identifier
shipment_id	INT, FK, nullable	Associated shipment
incident_type	VARCHAR	Temperature excursion, sensor failure, etc.
severity	VARCHAR	Low, medium, high, critical
detected_at	DATETIME	Detection time
start_time	DATETIME, nullable	Estimated or confirmed start
end_time	DATETIME, nullable	Estimated or confirmed end
incident_status	VARCHAR	Open, investigating, resolved, etc.
description	TEXT	Incident details

Not every incident must be associated with a shipment. A refrigeration failure in a warehouse could affect products stored at that facility.

For a more complete design, we can add a separate IncidentAsset or IncidentScope table to associate an incident with a shipment, facility, vehicle or sensor.

Table 13: IncidentReading

Links incidents to relevant sensor readings.

Attribute	Type	Description
incident_id	INT, PK/FK	Incident
reading_id	BIGINT, PK/FK	Relevant sensor reading
relevance_note	VARCHAR, nullable	Reason for inclusion

This allows investigators to associate multiple readings with an incident without duplicating the underlying measurements.

Table 14: IncidentBatch

Records which batches are potentially affected by an incident.

Attribute	Type	Description
incident_id	INT, PK/FK	Incident
batch_id	INT, PK/FK	Potentially affected batch
assessment_status	VARCHAR	Pending review, assessed, etc.
assessment_note	TEXT, nullable	Investigation notes

This is a critical relationship.

A single incident may affect several batches, and one batch might be involved in multiple incidents over its lifecycle.

Table 15: Investigation
Attribute	Type	Description
investigation_id	INT, PK	Investigation identifier
incident_id	INT, FK	Associated incident
assigned_to	INT, FK	Assigned investigator
started_at	DATETIME	Investigation start
completed_at	DATETIME, nullable	Completion time
findings	TEXT	Investigation findings
investigation_status	VARCHAR	Assigned, in progress, completed, etc.

A separate investigation table allows the incident record to remain the central event while investigation work is tracked independently.

Table 16: Staff
Attribute	Type	Description
staff_id	INT, PK	Staff identifier
staff_name	VARCHAR	Staff member's name
role	VARCHAR	Operator, investigator, quality manager, etc.
email	VARCHAR, UNIQUE	Work email
account_status	VARCHAR	Active or inactive
Table 17: CorrectiveAction
Attribute	Type	Description
action_id	INT, PK	Corrective-action identifier
investigation_id	INT, FK	Related investigation
assigned_to	INT, FK	Responsible staff member
action_description	TEXT	Action required
due_date	DATE, nullable	Target completion date
completed_at	DATETIME, nullable	Completion time
action_status	VARCHAR	Pending, in progress, completed

This enables multiple corrective actions for a single investigation.

5. How the relationships fit together

The core entity relationships are:

PHARMACEUTICAL_PRODUCT
          |
          | 1:N
          v
         BATCH
          |
          | N:M
          v
      SHIPMENT_BATCH
          ^
          | N:1
          |
       SHIPMENT
          |
          | 1:N
          v
  SHIPMENT_CHECKPOINT


SENSOR
   |
   | 1:N
   v
SENSOR_READING
   |
   | N:M
   v
INCIDENT_READING
   ^
   | N:1
   |
INCIDENT
   |
   | N:M
   v
INCIDENT_BATCH
   |
   | N:1
   v
  BATCH


INCIDENT
   |
   | 1:N
   v
INVESTIGATION
   |
   | 1:N
   v
CORRECTIVE_ACTION

The full ER diagram would also include facilities, vehicles, sensor assignments, batch movements and staff.

This is enough to give us a substantial ER model without making the first implementation unmanageable.

6. The actual user interface

We should build a web application with a simple dashboard.

It does not need to look like a commercial pharmaceutical platform. It needs to be clear, functional and easy to demonstrate.

I recommend the following screens.

Screen 1: Dashboard

Display:

Active shipments.
Open incidents.
Batches under investigation.
Overdue corrective actions.
Recent temperature excursions.
Shipments awaiting arrival confirmation.

The numbers should come from SQL queries, not manually entered dashboard values.

Screen 2: Product and batch management

Users can:

Register a pharmaceutical product.
Create a batch.
Record its expiry date.
View recorded quantities.
View current batch status.
Inspect its movement history.
Screen 3: Shipment management

Users can:

Create a shipment.
Assign a vehicle.
Add batches and quantities.
Record dispatch and arrival.
Add checkpoints.
View the shipment timeline.
Screen 4: Monitoring dashboard

Users can:

View recent readings.
Select a shipment or sensor.
Filter by time.
View readings outside configured limits.
Inspect missing or invalid readings.

A graph would be useful but is optional.

Screen 5: Incident investigation

This is our primary demo screen.

A user opens an incident and sees:

INCIDENT INC0042

Type: Temperature excursion
Shipment: SH001
Status: Under investigation

Relevant readings:
10:00 AM     5.2°C
10:05 AM     5.8°C
10:10 AM     8.6°C
10:15 AM    10.1°C

Potentially affected batches:
B001
B002
B005

Investigation:
Assigned to: Quality Officer 03

Actions:
[View Batch History]
[Record Finding]
[Place Batch on Hold]
[Add Corrective Action]

The available actions must be governed by user permissions and workflow rules.

Screen 6: Batch traceability

A user selects a batch and views:

Product details.
Shipment history.
Recorded facilities.
Relevant sensor readings.
Associated incidents.
Investigation outcomes.
Current recorded disposition.
Screen 7: Reports

Generate reports for:

Incidents by type and severity.
Batches associated with incidents.
Shipment histories.
Repeated incidents involving the same vehicle.
Corrective actions pending completion.
Expiring batches.
Sensor data-quality problems.

These features create plenty of scope for joins, grouping, subqueries and validation.

7. How we satisfy the DBMS requirements

This project has been selected partly because it provides substantial DBMS work beyond simply creating tables.

Requirement	Our implementation
Requirement specification	Define inventory, shipment, monitoring and incident workflows
ER diagram	Model products, batches, shipments, sensors, incidents and investigations
Relational schema	Convert the ER model into relational tables
Normalisation up to 3NF	Separate product, batch, shipment, sensor and incident information
SQL queries	CRUD operations, joins, aggregations, subqueries and reports
Constraints	Primary keys, foreign keys, uniqueness and check constraints
Transactions	Dispatching shipments, receiving inventory, recording movements and resolving incidents
Forms	Product registration, shipment creation, incident investigation and batch tracing
Security	Authentication and role-based permissions
Validation	Validate dates, quantities, status transitions and measurements
Testing	Test valid workflows, invalid inputs, constraints and concurrent updates
DFD Levels 0–2	Show data movement through the application
Demo	Simulate an excursion and trace affected batches through the supply chain
Example transaction

Suppose a warehouse dispatches a batch to a distribution centre.

The operation might involve:

Creating a shipment.
Associating the batch with it.
Recording the dispatched quantity.
Updating the relevant inventory records.
Recording the movement history.

These changes should be handled transactionally so that the database does not end up with a shipment record but no corresponding inventory movement if part of the operation fails.

This gives us a meaningful example of database transaction management.

8. How we should normalise the schema

For the DBMS assignment, we need to explain why the tables are structured this way.

Consider a poorly designed table:

ShipmentID
ShipmentDate
VehicleNumber
BatchNumber
ProductName
ProductExpiry
SensorID
Temperature
IncidentID
InvestigatorName

Imagine storing every sensor reading in this one table.

A shipment with 10,000 readings would repeat its vehicle details, batch details and product details thousands of times.

This creates:

Unnecessary duplication.
Update anomalies.
Insertion difficulties.
Deletion anomalies.

Our normalised design separates these concepts.

For example:

PharmaceuticalProduct
          |
          v
         Batch
          |
          v
    ShipmentBatch
          |
          v
       Shipment
          |
          v
   SensorAssignment
          |
          v
    SensorReading

The relationships are represented through primary and foreign keys.

For 3NF, we will examine the functional dependencies of each table, ensure attributes depend on the appropriate key, and remove transitive dependencies where present.

Important: we should not claim that a schema is in 3NF simply because it has many tables. We need to document the actual functional dependencies and candidate keys for the final schema.

9. The research component: our learned-index experiment

Now let's connect this application to the research idea we discussed earlier.

Remember: the application and the research experiment are related, but they are not the same thing.

The application stores pharmaceutical logistics information.

The experiment investigates how different indexing approaches behave under controlled workloads.

The problem we want to investigate

Suppose the system stores millions of sensor readings.

At first, the workload is stable.

Queries are distributed relatively evenly across shipments and time intervals.

Then a temperature incident occurs.

Operators begin issuing many queries about a particular shipment and time period. New readings also continue arriving.

We want to investigate whether an indexing strategy can maintain good performance when the data and query patterns change.

The experimental configurations

We can compare:

A conventional B+ tree.
An existing dynamic learned index.
Our proposed adaptation policy, if implementation and literature review justify a distinct policy.

The third configuration is a research hypothesis, not a proven improvement.

The workload phases
Phase	What we simulate	What we measure
Stable operation	Normal reading ingestion and queries	Baseline performance
Increased ingestion	A large increase in incoming readings	Insert latency and throughput
Localised incident	Many new readings concentrated in particular key ranges	Lookup latency and prediction error
Incident investigation	Repeated queries concerning a small set of shipments	Query latency and throughput
Incident recovery	Query activity returns toward normal	Recovery behaviour and maintenance cost
Combined change	Incoming data and query patterns change together	Overall system behaviour
The metrics

We should measure:

Median lookup latency.
95th-percentile and 99th-percentile lookup latency.
Range-query latency.
Insert/update latency.
Throughput.
Memory consumption.
Index prediction error, where applicable.
Time spent adapting.
Maintenance cost.

The experiments must use equivalent workload traces and comparable hardware conditions.

We should not claim a particular percentage improvement until we have run the benchmarks.

How the components fit together
       PHARMATRACE APPLICATION
                 |
                 v
       Pharmaceutical database
                 |
                 v
       Simulated workload generator
                 |
                 v
       Index benchmarking harness
                 |
       +---------+---------+
       |         |         |
       v         v         v
      B+       Existing   Proposed
     Tree      Learned    Adaptation
                Index      Policy
       |         |         |
       +---------+---------+
                 |
                 v
       Performance comparison
                 |
                 v
          Research findings

The initial benchmark may run independently from the application's production-style SQL queries. That is the most feasible starting point.

If we later integrate the learned index with a database engine, we can investigate end-to-end application query performance. We should not pretend that such integration already exists.

10. What makes the project distinctive?

We need to be honest here.

Pharmaceutical cold-chain monitoring is already an established field. A 2024 paper describes a big-data-based pharmaceutical cold-chain risk assessment and early-warning system, while a 2025 study examines temperature outlier detection during pharmaceutical transportation.

Therefore, these claims would be weak:

"We invented pharmaceutical temperature monitoring."
"No one has built a pharmaceutical traceability system before."
"Our database is the first to detect temperature excursions."

We cannot support those claims.

Instead, our application will focus on a well-defined workflow:

Environmental incident → batch identification → supply-chain traceability → investigation → documented corrective action.

This gives us a clear product concept.

Our potential research contribution is separate: investigating whether a particular learned-index adaptation strategy offers a measurable advantage under workload patterns motivated by this application.

We must conduct a more targeted literature review before claiming that the strategy itself is novel.

11. Recommended technology stack

For the first version, I would keep the stack relatively simple.

Component	Recommendation	Purpose
Relational database	PostgreSQL	Store application records
Backend	Python with FastAPI	Implement application logic and APIs
Frontend	React	Build the dashboard and forms
Data generation	Python	Generate realistic synthetic shipments and sensor readings
Charts	A React-compatible charting library	Display temperature and incident timelines
Authentication	Backend-managed authentication and role permissions	Restrict sensitive operations
Research benchmark	C++ or a compatible implementation language for the selected index	Evaluate index performance

You do not need to implement every technology immediately.

For the DBMS mini-project, the priority should be:

Relational schema.
SQL queries.
Constraints and transactions.
Working application forms.
Validation and testing.
ER diagram and DFDs.
Research benchmark.

We can add more sophisticated components after the basic application works.

12. How we will test the application

We should prepare a test plan before building the complete application.

Here are examples of tests we can perform.

Test	Input or action	Expected behaviour
T01	Register a valid pharmaceutical product	Product is saved
T02	Register a duplicate batch number	Database rejects the duplicate
T03	Create a shipment with a nonexistent vehicle	Foreign-key validation rejects it
T04	Add a batch to a shipment	Shipment-batch association is saved
T05	Record a valid sensor reading	Reading is saved
T06	Record a reading outside the configured limits	Reading is saved and an appropriate excursion rule is evaluated
T07	Create an incident	Incident is stored and linked to relevant records
T08	Trace affected batches	Correct associated batches are returned
T09	Attempt an unauthorised quality-status change	Operation is rejected
T10	Fail part of an inventory transaction	The transaction is rolled back
T11	Complete an investigation	Findings and completion time are recorded
T12	Generate an incident report	Results match the underlying database records

We should also test missing readings, invalid timestamps, duplicate events and repeated incident notifications.

These tests will help with the rubric's testing component.

13. The final demonstration we should aim for

The demo should tell a coherent story rather than simply show tables.

Scene 1: Normal operation

Show the dashboard with active shipments and normal sensor readings.

Scene 2: Simulate a refrigeration failure

Generate a sequence of readings that violates the configured monitoring rule.

Scene 3: Show the incident

The application creates an incident and displays the relevant readings.

Scene 4: Trace affected batches

The system identifies batches associated with the shipment and shows their recorded movement history.

Scene 5: Investigate

An authorised user assigns an investigator, records findings and documents corrective actions.

Scene 6: Resolve

The application displays the updated incident and batch statuses.

Scene 7: Show the database

Demonstrate the underlying SQL queries, relationships, constraints and transaction behaviour.

Scene 8: Present the research experiment

Show benchmark results comparing the indexing configurations under stable and incident-driven workloads.

That final separation is important: the application demonstrates the business workflow; the benchmark demonstrates the database research.

14. Scope control: what we should build first

This project could become quite large, so we need to avoid trying to implement everything at once.

Phase 1 — Essential DBMS application

Build:

Products and batches.
Facilities and shipments.
Shipment-batch relationships.
Sensors and readings.
Incidents.
Investigations and corrective actions.
Basic dashboard and reports.

This is the minimum complete application.

Phase 2 — Improve traceability

Add:

Shipment checkpoints.
Batch movement history.
Incident-to-reading associations.
Incident-to-batch associations.
Role-based permissions.
Audit history.
Phase 3 — Research benchmark

Build:

Synthetic workload generator.
B+ tree baseline.
Existing dynamic learned-index baseline.
Benchmark collection and reporting.
Controlled workload changes.
Phase 4 — Experimental improvement

Only after the literature review and baseline experiments:

Define a specific weakness worth addressing.
Implement a distinguishable adaptation policy.
Compare it against the existing baselines.
Report successful and unsuccessful cases.

This order keeps the project feasible and prevents the research component from blocking the required DBMS application.

15. Final project definition

Here is the concise version we should use when explaining the concept to faculty.

Project: PharmaTrace: Pharmaceutical Cold-Chain Integrity, Traceability and Incident Management System.

Problem: Temperature-sensitive pharmaceutical products pass through multiple storage and transportation stages. When an environmental excursion occurs, organisations need to trace the affected shipments and batches, reconstruct relevant conditions and locations, and document investigations and corrective actions.

Proposed application: A relational database system that manages pharmaceutical products, batches, shipments, facilities, sensors, readings, incidents, investigations and corrective actions.

Core functionality: Shipment tracking, sensor-reading storage, configurable excursion rules, incident creation, batch traceability, investigation management, inventory-status tracking and reporting.

DBMS contribution: A normalised relational schema, ER diagram, DFD Levels 0–2, SQL operations, constraints, transactions, forms, security, validation and testing.

Research component: An experimental study of learned-index performance under changing data and query workloads motivated by pharmaceutical incident-response scenarios.

Expected deliverables: A working web application, database schema, SQL scripts, diagrams, test report, demonstration and a benchmark report.

Research caveat: The project does not claim that pharmaceutical cold-chain monitoring or adaptive learned indexing is itself novel. Any claim of technical novelty must be established through literature review and experimental evidence.