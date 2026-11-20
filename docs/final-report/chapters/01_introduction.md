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
