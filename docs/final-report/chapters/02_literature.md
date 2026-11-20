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
