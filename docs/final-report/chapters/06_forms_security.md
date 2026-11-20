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
