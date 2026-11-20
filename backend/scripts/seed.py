"""Deterministic demo data, relative to the time it is run.

It goes through the same functions and triggers as the application (dispatch_shipment,
receive_shipment, excursion detection, workflow rules), so the data is consistent.

Demo logins (password = the part before @ followed by "123", e.g. operator123):
    admin@pharmatrace.local, operator@..., investigator@..., investigator2@..., qm@...
"""

import math
import random
from datetime import UTC, date, datetime, timedelta

import psycopg
from pwdlib import PasswordHash

from app.config import get_settings

STAFF = [
    ("Asha Rao", "admin@pharmatrace.local", "admin123", "admin"),
    ("Ravi Kumar", "operator@pharmatrace.local", "operator123", "operator"),
    ("Meera Nair", "investigator@pharmatrace.local", "investigator123", "investigator"),
    ("Vikram Shah", "investigator2@pharmatrace.local", "investigator2123", "investigator"),
    ("Priya Menon", "qm@pharmatrace.local", "qm123", "quality_manager"),
]
PRODUCTS = [  # name, type, min, max, min RH, max RH  (illustrative configured limits)
    ("Vaccine A", "vaccine", 2, 8, None, None),
    ("Insulin B", "medicine", 2, 8, None, None),
    ("Biologic C", "biologic", 2, 8, None, None),
    ("Tablet D", "medicine", 15, 25, 30, 65),
]
FACILITIES = [  # name, type, street, city, pincode, phones
    ("Central Warehouse", "warehouse", "14 Industrial Area, Peenya", "Bengaluru", "560058", ["080-28390011", "080-28390012"]),
    ("Regional DC Mysuru", "distribution_centre", "Plot 7, Hebbal Industrial Area", "Mysuru", "570016", ["0821-2401111"]),
    ("City General Hospital", "hospital", "1 Hospital Road", "Bengaluru", "560001", ["080-22970000"]),
    ("Mysuru District Hospital", "hospital", "Irwin Road", "Mysuru", "570001", ["0821-2423300"]),
    ("Tumakuru Community Clinic", "clinic", "BH Road", "Tumakuru", "572101", ["0816-2272727"]),
    ("Hubballi Care Pharmacy", "pharmacy", "Station Road", "Hubballi", "580020", ["0836-2350505"]),
]
VEHICLES = [
    ("KA01AB1234", "refrigerated_van", "operational"),
    ("KA05CD5678", "refrigerated_truck", "operational"),
    ("KA09EF9012", "refrigerated_van", "degraded"),
    ("KA03GH3456", "insulated_van", "operational"),
]


def seed(db_name: str | None = None) -> None:
    s = get_settings()
    rnd = random.Random(42)
    hasher = PasswordHash.recommended()
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    now -= timedelta(minutes=now.minute % 5)
    t0 = now - timedelta(days=20)
    today = now.date()

    with psycopg.connect(s.url("pharmatrace_owner", s.pg_owner_password, db_name)) as conn:
        cur = conn.cursor()

        def one(query, params=()):
            return cur.execute(query, params).fetchone()[0]

        def as_staff(staff_id, reason=""):
            cur.execute("SELECT set_config('app.current_staff_id', %s, true), set_config('app.change_reason', %s, true)",
                        [str(staff_id), reason])

        # ---------------------------------------------------------- master data
        staff = {}
        for name, email, pw, role in STAFF:
            staff[role if role not in staff else role + "2"] = one(
                "INSERT INTO staff (staff_name, email, password_hash, role) VALUES (%s,%s,%s,%s) RETURNING staff_id",
                [name, email, hasher.hash(pw), role])
        admin, op, inv, inv2, qm = (staff["admin"], staff["operator"], staff["investigator"],
                                   staff["investigator2"], staff["quality_manager"])
        as_staff(admin, "initial data load")

        prod = {}
        for name, ptype, lo, hi, hlo, hhi in PRODUCTS:
            prod[name] = one("""INSERT INTO product (product_name, product_type, min_temp, max_temp, min_humidity, max_humidity)
                                VALUES (%s,%s,%s,%s,%s,%s) RETURNING product_id""", [name, ptype, lo, hi, hlo, hhi])

        fac = {}
        for name, ftype, street, city, pin, phones in FACILITIES:
            fac[name] = one("""INSERT INTO facility (facility_name, facility_type, street, city, pincode)
                               VALUES (%s,%s,%s,%s,%s) RETURNING facility_id""", [name, ftype, street, city, pin])
            for ph in phones:
                cur.execute("INSERT INTO facility_phone VALUES (%s,%s)", [fac[name], ph])
        wh, dc = fac["Central Warehouse"], fac["Regional DC Mysuru"]

        veh = {}
        for reg, vtype, status in VEHICLES:
            veh[reg] = one("""INSERT INTO vehicle (registration_number, vehicle_type, refrigeration_status)
                              VALUES (%s,%s,%s) RETURNING vehicle_id""", [reg, vtype, status])

        batches = [  # number, product, qty, expiry
            ("B001", "Vaccine A", 5000, date(2027, 6, 30)), ("B002", "Vaccine A", 3000, date(2027, 8, 31)),
            ("B003", "Insulin B", 2000, date(2027, 3, 31)), ("B004", "Vaccine A", 1500, date(2027, 9, 30)),
            ("B005", "Biologic C", 800, date(2027, 1, 31)), ("B006", "Insulin B", 1200, date(2027, 5, 31)),
            ("B007", "Vaccine A", 2500, date(2027, 11, 30)), ("B008", "Biologic C", 600, date(2027, 2, 28)),
            ("B009", "Tablet D", 10000, date(2028, 4, 30)), ("B010", "Tablet D", 8000, date(2028, 6, 30)),
            ("B011", "Vaccine A", 1000, today - timedelta(days=5)),     # already expired
            ("B012", "Insulin B", 900, today + timedelta(days=20)),     # expiring soon
        ]
        bat = {}
        for number, pname, qty, expiry in batches:
            mfg = min(expiry - timedelta(days=400), today - timedelta(days=60))
            bat[number] = one("""INSERT INTO batch (batch_number, product_id, manufacturing_date, expiry_date, initial_quantity)
                                 VALUES (%s,%s,%s,%s,%s) RETURNING batch_id""", [number, prod[pname], mfg, expiry, qty])
            cur.execute("""INSERT INTO batch_movement (batch_id, facility_id, movement_type, movement_time, quantity_moved)
                           VALUES (%s,%s,'received',%s,%s)""", [bat[number], wh, t0, qty])

        sensors = {}
        for i in range(1, 11):
            stype = "temp_humidity" if i == 6 else "temperature"
            status = {9: "inactive", 10: "faulty"}.get(i, "active")
            sensors[i] = one("""INSERT INTO sensor (serial_number, sensor_type, installation_status)
                                VALUES (%s,%s,%s) RETURNING sensor_id""", [f"TL-{1000 + i}", stype, status])

        # ---------------------------------------------------------- shipments
        def shipment(vehicle, origin, dest, dispatch_at, hours, lines, sensor_no, deliver=True):
            sid = one("""INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
                         VALUES (%s,%s,%s,%s) RETURNING shipment_id""",
                      [veh[vehicle], origin, dest, dispatch_at + timedelta(hours=hours)])
            for number, qty in lines:
                cur.execute("INSERT INTO shipment_batch VALUES (%s,%s,%s)", [sid, bat[number], qty])
            cur.execute("""INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at)
                           VALUES (%s,%s,%s)""", [sensors[sensor_no], sid, dispatch_at - timedelta(minutes=30)])
            if dispatch_at <= now:
                as_staff(op, "dispatch")
                cur.execute("SELECT dispatch_shipment(%s, %s)", [sid, dispatch_at])
                cur.execute("""INSERT INTO shipment_checkpoint VALUES (%s, 2, %s, 'transit_scan', 'Highway toll plaza scan')""",
                            [sid, dispatch_at + timedelta(minutes=95)])
                if deliver:
                    cur.execute("SELECT receive_shipment(%s, %s)", [sid, dispatch_at + timedelta(hours=hours)])
            return sid

        # facility sensor at the distribution centre
        cur.execute("INSERT INTO sensor_assignment (sensor_id, facility_id, assigned_at) VALUES (%s,%s,%s)",
                    [sensors[1], dc, t0])

        d1 = now - timedelta(days=15)
        shipment("KA01AB1234", wh, dc, d1, 5, [("B001", 2000), ("B002", 1000), ("B005", 300)], 2)
        d2 = now - timedelta(days=10)
        sh2 = shipment("KA09EF9012", wh, fac["City General Hospital"], d2, 4, [("B004", 1000), ("B003", 500)], 3)
        d3 = now - timedelta(days=5)
        sh3 = shipment("KA09EF9012", dc, fac["Mysuru District Hospital"], d3, 4, [("B001", 800), ("B005", 200)], 4)
        d4 = now - timedelta(hours=3)
        shipment("KA05CD5678", wh, fac["Tumakuru Community Clinic"], d4, 5,
                       [("B002", 500), ("B006", 400), ("B007", 600)], 5, deliver=False)
        d5 = now - timedelta(hours=6)
        shipment("KA03GH3456", wh, fac["Hubballi Care Pharmacy"], d5, 5, [("B009", 3000)], 6, deliver=False)
        sh6 = one("""INSERT INTO shipment (vehicle_id, origin_facility_id, destination_facility_id, expected_arrival)
                     VALUES (%s,%s,%s,%s) RETURNING shipment_id""",
                  [veh["KA01AB1234"], wh, fac["City General Hospital"], now + timedelta(days=1)])
        cur.execute("INSERT INTO shipment_batch VALUES (%s,%s,300), (%s,%s,200)", [sh6, bat["B007"], sh6, bat["B012"]])
        cur.execute("INSERT INTO sensor_assignment (sensor_id, shipment_id, assigned_at) VALUES (%s,%s,%s)",
                    [sensors[7], sh6, now - timedelta(hours=1)])

        # ---------------------------------------------------------- readings
        rows = []

        def series(sensor_no, start, end, base=5.0, spikes=None, humidity=None, skip=None):
            t, k = start, 0
            while t <= end:
                if not (skip and skip[0] <= t < skip[1]):
                    temp = base + 0.6 * math.sin(k / 12) + rnd.uniform(-0.25, 0.25)
                    if spikes and k - spikes[0] in range(len(spikes[1])):
                        temp = spikes[1][k - spikes[0]]
                    hum = None if humidity is None else round(humidity + rnd.uniform(-4, 4), 1)
                    rows.append((sensors[sensor_no], t, t + timedelta(seconds=20), round(temp, 2), hum))
                t += timedelta(minutes=5)
                k += 1

        series(1, t0, now, base=4.8, skip=(now - timedelta(days=2, hours=3), now - timedelta(days=2, hours=2, minutes=20)))
        series(2, d1, d1 + timedelta(hours=5))
        series(3, d2, d2 + timedelta(hours=4),
               spikes=(20, [7.5, 8.4, 9.6, 10.8, 11.4, 10.9, 9.7, 8.5, 7.6, 6.5]))
        series(4, d3, d3 + timedelta(hours=4), spikes=(24, [7.2, 8.3, 8.9, 9.3, 8.8, 8.1, 7.4]))
        series(5, d4, now)
        series(6, d5, now, base=21.0, humidity=50)
        rows.sort(key=lambda r: r[1])
        cur.executemany("""INSERT INTO sensor_reading (sensor_id, recorded_at, ingested_at, temperature, humidity)
                           VALUES (%s,%s,%s,%s,%s)""", rows)
        # data-quality examples: a corrupt value, and readings from a faulty unassigned sensor
        cur.execute("""INSERT INTO sensor_reading (sensor_id, recorded_at, ingested_at, temperature)
                       VALUES (%s, %s, %s, 999.0)""",
                    [sensors[1], now - timedelta(days=1, minutes=2), now - timedelta(days=1)])
        cur.executemany("""INSERT INTO sensor_reading (sensor_id, recorded_at, ingested_at, temperature)
                           VALUES (%s,%s,%s,%s)""",
                        [(sensors[10], now - timedelta(hours=h), now - timedelta(hours=h), 4.0 + h / 10) for h in range(1, 7)])

        # ---------------------------------------------------------- incident 1 (SH2): fully investigated and closed
        inc1 = one("SELECT incident_id FROM incident WHERE shipment_id = %s", [sh2])
        inc1_detected = one("SELECT detected_at FROM incident WHERE incident_id = %s", [inc1])
        as_staff(qm, "investigator assigned")
        iv1 = one("""INSERT INTO investigation (incident_id, assigned_to, started_at, investigation_status)
                     VALUES (%s,%s,%s,'in_progress') RETURNING investigation_id""",
                  [inc1, inv, inc1_detected + timedelta(hours=1)])
        as_staff(inv, "assessment after data-logger review")
        for number, note in (("B004", "Peak 11.4 °C for about 40 minutes; within the manufacturer's stability data."),
                             ("B003", "Insulin exposure above limit; stability data does not cover it.")):
            cur.execute("""UPDATE incident_batch SET assessment_status = 'assessed', assessment_note = %s
                           WHERE incident_id = %s AND batch_id = %s""", [note, inc1, bat[number]])
            cur.execute("UPDATE batch SET batch_status = 'on_hold' WHERE batch_id = %s", [bat[number]])
        cur.execute("""INSERT INTO corrective_action (investigation_id, assigned_to, action_description, due_date,
                                                       completed_at, action_status)
                       VALUES (%s,%s,'Replace the door seal of vehicle KA09EF9012',%s,%s,'completed'),
                              (%s,%s,'Retrain drivers on pre-cooling before loading',%s,%s,'completed')""",
                    [iv1, op, (d2 + timedelta(days=3)).date(), d2 + timedelta(days=2),
                     iv1, qm, (d2 + timedelta(days=5)).date(), d2 + timedelta(days=4)])
        cur.execute("""UPDATE investigation SET investigation_status = 'completed', completed_at = %s,
                       findings = 'Door seal on KA09EF9012 failed; cabin warmed for about 40 minutes.'
                       WHERE investigation_id = %s""", [inc1_detected + timedelta(days=1), iv1])
        as_staff(qm, "quality review complete")
        cur.execute("UPDATE batch SET batch_status = 'released' WHERE batch_id = %s", [bat["B004"]])
        cur.execute("UPDATE batch SET batch_status = 'quarantined' WHERE batch_id = %s", [bat["B003"]])
        cur.execute("UPDATE batch SET batch_status = 'disposed' WHERE batch_id = %s", [bat["B003"]])
        cur.execute("""INSERT INTO batch_movement (batch_id, facility_id, movement_type, movement_time, quantity_moved)
                       VALUES (%s,%s,'disposed',%s,500)""",
                    [bat["B003"], fac["City General Hospital"], d2 + timedelta(days=6)])
        cur.execute("UPDATE incident SET incident_status = 'resolved' WHERE incident_id = %s", [inc1])
        cur.execute("UPDATE incident SET incident_status = 'closed' WHERE incident_id = %s", [inc1])

        # ---------------------------------------------------------- incident 2 (SH3): under investigation
        inc2 = one("SELECT incident_id FROM incident WHERE shipment_id = %s", [sh3])
        inc2_detected = one("SELECT detected_at FROM incident WHERE incident_id = %s", [inc2])
        as_staff(qm, "investigator assigned")
        iv2 = one("""INSERT INTO investigation (incident_id, assigned_to, started_at, investigation_status)
                     VALUES (%s,%s,%s,'in_progress') RETURNING investigation_id""",
                  [inc2, inv2, inc2_detected + timedelta(hours=2)])
        as_staff(inv2, "hold pending review of second excursion on the same vehicle")
        cur.execute("UPDATE batch SET batch_status = 'on_hold' WHERE batch_id = %s", [bat["B005"]])
        cur.execute("""UPDATE incident_batch SET assessment_status = 'under_assessment'
                       WHERE incident_id = %s AND batch_id = %s""", [inc2, bat["B005"]])
        cur.execute("""INSERT INTO corrective_action (investigation_id, assigned_to, action_description, due_date)
                       VALUES (%s,%s,'Service the refrigeration unit of KA09EF9012',%s)""",
                    [iv2, op, today - timedelta(days=1)])

        conn.commit()
        counts = cur.execute("""SELECT (SELECT COUNT(*) FROM sensor_reading), (SELECT COUNT(*) FROM incident),
                                       (SELECT COUNT(*) FROM shipment)""").fetchone()
        print(f"  seeded {counts[0]} readings, {counts[1]} incidents, {counts[2]} shipments")


if __name__ == "__main__":
    seed()
