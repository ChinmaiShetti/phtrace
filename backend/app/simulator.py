"""Simulated sensor feed (no physical sensors in this project).

backfill(): normal readings for every active assignment, from its last reading up to now.
excursion(): a live refrigeration failure on one shipment, one reading every few seconds.
"""

import math
import random
import threading
import time
from datetime import UTC, datetime, timedelta

from app import db

INSERT = """INSERT INTO sensor_reading (sensor_id, recorded_at, temperature, humidity)
            VALUES (%s, %s, %s, %s) ON CONFLICT (sensor_id, recorded_at) DO NOTHING"""


def _normal_temp(lo: float, hi: float, k: int, rnd: random.Random) -> float:
    mid = (lo + hi) / 2 if hi - lo < 15 else lo + 5
    return round(mid + 0.6 * math.sin(k / 12) + rnd.uniform(-0.25, 0.25), 2)


def backfill(staff_id: int | None = None) -> int:
    """Fill gaps since the last reading of each active assignment with in-range readings."""
    rnd = random.Random()
    now = datetime.now(UTC)
    inserted = 0
    for conn in db.transaction(staff_id):
        targets = conn.execute("""
            SELECT a.sensor_id, s.sensor_type, s.expected_interval_s,
                   GREATEST(a.assigned_at,
                            (SELECT MAX(recorded_at) FROM sensor_reading r WHERE r.sensor_id = a.sensor_id)) AS since,
                   COALESCE(l.min_temp, fl.min_temp, 2) AS lo, COALESCE(l.max_temp, fl.max_temp, 8) AS hi,
                   COALESCE(l.min_humidity, 40) AS hlo, COALESCE(l.max_humidity, 60) AS hhi
            FROM sensor_assignment a JOIN sensor s USING (sensor_id)
            LEFT JOIN shipment sh ON sh.shipment_id = a.shipment_id
            LEFT JOIN v_shipment_limits l ON l.shipment_id = a.shipment_id
            LEFT JOIN LATERAL (
                SELECT MAX(p.min_temp) AS min_temp, MIN(p.max_temp) AS max_temp
                FROM batches_at_target(NULL, a.facility_id, now()) t JOIN batch b USING (batch_id)
                JOIN product p USING (product_id)) fl ON a.facility_id IS NOT NULL
            WHERE a.unassigned_at IS NULL AND s.installation_status = 'active'
              AND (a.shipment_id IS NULL OR sh.shipment_status = 'in_transit')""").fetchall()
        for t in targets:
            step = timedelta(seconds=t["expected_interval_s"])
            ts, k = t["since"] + step, 0
            while ts <= now:
                hum = round((t["hlo"] + t["hhi"]) / 2 + rnd.uniform(-3, 3), 1) if t["sensor_type"] != "temperature" else None
                temp = _normal_temp(float(t["lo"]), float(t["hi"]), k, rnd) if t["sensor_type"] != "humidity" else None
                inserted += conn.execute(INSERT, [t["sensor_id"], ts, temp, hum]).rowcount
                ts += step
                k += 1
    return inserted


def excursion_profile(start: float, peak: float, steps: int = 14) -> list[float]:
    """Temperature rises to the peak, holds briefly, then recovers (cooling restored)."""
    up = [start + (peak - start) * (i / 7) ** 1.3 for i in range(1, 8)]
    hold = [peak + 0.2, peak - 0.1]
    down = [peak - (peak - start) * i / 5 for i in range(1, steps - len(up) - len(hold) + 1)]
    return [round(v, 2) for v in up + hold + down]


def run_excursion(shipment_id: int, peak: float, staff_id: int | None, interval_s: float = 2.5) -> None:
    for conn in db.transaction(staff_id):
        a = conn.execute("""SELECT a.sensor_id, l.max_temp FROM sensor_assignment a
                            JOIN v_shipment_limits l USING (shipment_id)
                            WHERE a.shipment_id = %s AND a.unassigned_at IS NULL LIMIT 1""", [shipment_id]).fetchone()
    if a is None:
        return
    start = float(a["max_temp"]) - 2.5
    for temp in excursion_profile(start, peak):
        for conn in db.transaction(staff_id):
            conn.execute(INSERT, [a["sensor_id"], datetime.now(UTC).replace(microsecond=0), temp, None])
        time.sleep(interval_s)


def start_excursion(shipment_id: int, peak: float, staff_id: int | None) -> None:
    threading.Thread(target=run_excursion, args=(shipment_id, peak, staff_id), daemon=True).start()
