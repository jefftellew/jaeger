import sqlite3
import os
from datetime import datetime, timezone


_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics.db')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time   TEXT
);

CREATE TABLE IF NOT EXISTS rat_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER NOT NULL REFERENCES missions(id),
    rat_id     TEXT    NOT NULL,
    event_type TEXT    NOT NULL,
    event_time TEXT    NOT NULL,
    zone       INTEGER,
    az         REAL,
    el         REAL,
    range_m    REAL
);

CREATE TABLE IF NOT EXISTS sensor_mode_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id  INTEGER NOT NULL REFERENCES missions(id),
    sensor_type TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    event_time  TEXT    NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FCPAnalyticsDB:
    """
    Thin SQLite wrapper for F2T2EA performance analytics.

    All timestamps are stored as ISO-8601 UTC strings so they survive
    application restarts and can be parsed back with datetime.fromisoformat().

    Usage
    -----
    db = FCPAnalyticsDB()
    db.start_mission()
    ...
    db.log_sensor_event('lidar', 'enabled')
    db.log_rat_event('RAT_001', 'detected', zone=1, az=12.3, el=5.0, range_m=800.0)
    ...
    db.end_mission()
    """

    def __init__(self, db_path: str = _DB_PATH):
        self._db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

        self._mission_id: int | None = None

    # ------------------------------------------------------------------
    # Mission lifecycle
    # ------------------------------------------------------------------

    def start_mission(self) -> int:
        """Open a new mission row and cache its id. Returns mission id."""
        cur = self._conn.execute(
            "INSERT INTO missions (start_time) VALUES (?)", (_now_iso(),)
        )
        self._conn.commit()
        self._mission_id = cur.lastrowid
        return self._mission_id

    def end_mission(self):
        """Stamp the current mission's end_time."""
        if self._mission_id is None:
            return
        self._conn.execute(
            "UPDATE missions SET end_time = ? WHERE id = ?",
            (_now_iso(), self._mission_id),
        )
        self._conn.commit()

    @property
    def mission_id(self) -> int | None:
        return self._mission_id

    # ------------------------------------------------------------------
    # Event logging
    # ------------------------------------------------------------------

    def log_rat_event(
        self,
        rat_id: str,
        event_type: str,
        zone: int | None = None,
        az: float | None = None,
        el: float | None = None,
        range_m: float | None = None,
        timestamp: str | None = None,
    ):
        """
        Log a RAT lifecycle event.

        event_type values: 'detected' | 'zone_change' | 'engage_commanded' | 'lost'
        """
        if self._mission_id is None:
            return
        self._conn.execute(
            """INSERT INTO rat_events
               (mission_id, rat_id, event_type, event_time, zone, az, el, range_m)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self._mission_id,
                rat_id,
                event_type,
                timestamp or _now_iso(),
                zone,
                az,
                el,
                range_m,
            ),
        )
        self._conn.commit()

    def log_sensor_event(self, sensor_type: str, event_type: str, timestamp: str | None = None):
        """
        Log a sensor mode change.

        sensor_type: 'lidar' | 'rf' | 'acoustic'
        event_type:  'enabled' | 'disabled'
        """
        if self._mission_id is None:
            return
        self._conn.execute(
            """INSERT INTO sensor_mode_events
               (mission_id, sensor_type, event_type, event_time)
               VALUES (?, ?, ?, ?)""",
            (self._mission_id, sensor_type, event_type, timestamp or _now_iso()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_sensor_durations(self, mission_id: int | None = None) -> dict:
        """
        Compute total enabled-duration (seconds) per sensor for a mission.

        Pairs consecutive 'enabled'/'disabled' events in chronological order.
        An 'enabled' with no following 'disabled' is treated as still-active
        and measured against now.

        Returns:
            {
              'lidar':    {'times_enabled': N, 'total_seconds': F, 'pct_mission': F},
              'rf':       {...},
              'acoustic': {...},
            }
        """
        mid = mission_id or self._mission_id
        result = {}

        mission_start, mission_end = self._mission_bounds(mid)
        mission_duration = 0.0

        if mission_end is not None:
            mission_duration = (mission_end - mission_start).total_seconds()
        else:
            mission_duration = (datetime.now(timezone.utc) - mission_start).total_seconds()

        for sensor in ('lidar', 'rf', 'acoustic'):
            rows = self._conn.execute(
                """SELECT event_type, event_time FROM sensor_mode_events
                   WHERE mission_id = ? AND sensor_type = ?
                   ORDER BY event_time ASC""",
                (mid, sensor),
            ).fetchall()

            total_s = 0.0
            times_enabled = 0
            pending_enable: datetime | None = None

            for row in rows:
                t = datetime.fromisoformat(row['event_time'])
                if row['event_type'] == 'enabled':
                    if pending_enable is None:   # ignore double-enables
                        pending_enable = t
                        times_enabled += 1
                elif row['event_type'] == 'disabled':
                    if pending_enable is not None:
                        total_s += (t - pending_enable).total_seconds()
                        pending_enable = None

            # still active at mission end
            if pending_enable is not None:
                cap = mission_end if mission_end else datetime.now(timezone.utc)
                total_s += (cap - pending_enable).total_seconds()

            pct = (total_s / mission_duration * 100.0) if mission_duration > 0 else 0.0
            result[sensor] = {
                'times_enabled': times_enabled,
                'total_seconds': total_s,
                'pct_mission': pct,
            }

        return result

    def get_time_to_engage(self, mission_id: int | None = None) -> list[dict]:
        """
        Return per-RAT timing rows for a mission.

        Each row:
            rat_id, detected_at, zone3_at, engage_at,
            detect_to_zone3_s, detect_to_engage_s
        Missing timestamps are returned as None; elapsed values as None too.
        """
        mid = mission_id or self._mission_id
        rows = self._conn.execute(
            """SELECT rat_id, event_type, MIN(event_time) AS first_time
               FROM rat_events
               WHERE mission_id = ?
               GROUP BY rat_id, event_type
               ORDER BY rat_id, first_time""",
            (mid,),
        ).fetchall()

        # Aggregate by rat_id
        by_rat: dict[str, dict] = {}
        for row in rows:
            rid = row['rat_id']
            if rid not in by_rat:
                by_rat[rid] = {}
            by_rat[rid][row['event_type']] = row['first_time']

        result = []
        for rat_id, events in by_rat.items():
            detected_str   = events.get('detected')
            zone3_str      = self._first_zone3_time(mid, rat_id)
            engage_str     = events.get('engage_commanded')

            detected_dt  = datetime.fromisoformat(detected_str)  if detected_str  else None
            zone3_dt     = datetime.fromisoformat(zone3_str)      if zone3_str     else None
            engage_dt    = datetime.fromisoformat(engage_str)     if engage_str    else None

            detect_to_zone3  = (zone3_dt  - detected_dt).total_seconds() if (detected_dt and zone3_dt)  else None
            detect_to_engage = (engage_dt - detected_dt).total_seconds() if (detected_dt and engage_dt) else None

            result.append({
                'rat_id':             rat_id,
                'detected_at':        detected_str,
                'zone3_at':           zone3_str,
                'engage_at':          engage_str,
                'detect_to_zone3_s':  detect_to_zone3,
                'detect_to_engage_s': detect_to_engage,
            })

        result.sort(key=lambda r: r['detected_at'] or '')
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mission_bounds(self, mission_id: int | None):
        """Return (start_datetime, end_datetime | None) for a mission."""
        if mission_id is None:
            return None, None
        row = self._conn.execute(
            "SELECT start_time, end_time FROM missions WHERE id = ?", (mission_id,)
        ).fetchone()
        if not row:
            return None, None
        start = datetime.fromisoformat(row['start_time']) if row['start_time'] else None
        end   = datetime.fromisoformat(row['end_time'])   if row['end_time']   else None
        return start, end

    def _first_zone3_time(self, mission_id: int, rat_id: str) -> str | None:
        """Return ISO timestamp of first zone_change to zone=3 for a RAT."""
        row = self._conn.execute(
            """SELECT MIN(event_time) AS t FROM rat_events
               WHERE mission_id = ? AND rat_id = ?
                 AND event_type = 'zone_change' AND zone = 3""",
            (mission_id, rat_id),
        ).fetchone()
        return row['t'] if row else None

    def close(self):
        self._conn.close()
