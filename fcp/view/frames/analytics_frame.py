import tkinter as tk
from tkinter import ttk
import csv
import os
from datetime import datetime, timezone

from view.frames.base_frame import BaseFrame


def _fmt_duration(seconds: float | None) -> str:
    """Format a duration in seconds as HH:MM:SS, or '---' if None."""
    if seconds is None:
        return '---'
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_elapsed(seconds: float | None) -> str:
    """Format elapsed seconds to one decimal place, or '---' if None."""
    if seconds is None:
        return '---'
    return f"{seconds:.1f} s"


def _fmt_ts(iso_str: str | None) -> str:
    """Shorten an ISO timestamp to HH:MM:SS.mmm local-time display."""
    if not iso_str:
        return '---'
    try:
        dt = datetime.fromisoformat(iso_str).astimezone()
        return dt.strftime('%H:%M:%S.') + f"{dt.microsecond // 1000:03d}"
    except Exception:
        return iso_str


class AnalyticsFrame(BaseFrame):
    """
    Displays F2T2EA performance analytics for the current mission.

    Live sections (populated from analytics DB):
        Sensor Mode Usage
        Time to Detect / Engage (per target)

    Stub sections (awaiting Effector / DNE integration):
        F2T2EA Event Rates & Durations
        Identification Accuracy
        Engagement Success Rate
        Losses per Target
    """

    # Auto-refresh interval in milliseconds
    _REFRESH_MS = 1_000

    def __init__(self, parent, db=None, **kwargs):
        """
        Parameters
        ----------
        parent : tk widget
        db     : FCPAnalyticsDB instance (injected after construction via set_db)
        """
        self._db = db
        self._refresh_job = None
        super().__init__(parent, **kwargs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_db(self, db):
        """Inject the analytics DB after construction if needed."""
        self._db = db

    def refresh(self):
        """Re-query the DB and redraw all live tables."""
        if self._db is None:
            return
        self._populate_sensor_table()
        self._populate_t2e_table()

    # ------------------------------------------------------------------
    # Widget construction (called by BaseFrame.__init__)
    # ------------------------------------------------------------------

    def create_widgets(self):
        self.columnconfigure(0, weight=1)

        outer = ttk.LabelFrame(self, text='Performance Analytics')
        outer.grid(row=0, column=0, padx=6, pady=6, sticky='nsew')
        outer.columnconfigure(0, weight=1)

        # ---- Section A: Sensor Mode Usage ----------------------------
        sensor_lf = ttk.LabelFrame(outer, text='Sensor Mode Usage')
        sensor_lf.grid(row=0, column=0, padx=6, pady=(6, 2), sticky='nsew')
        sensor_lf.columnconfigure(0, weight=1)

        sensor_cols = ('sensor', 'times_enabled', 'total_duration', 'pct_mission')
        self._sensor_tree = ttk.Treeview(
            sensor_lf, columns=sensor_cols, show='headings', height=3
        )
        self._sensor_tree.heading('sensor',        text='Sensor')
        self._sensor_tree.heading('times_enabled', text='Times Enabled')
        self._sensor_tree.heading('total_duration', text='Total Duration')
        self._sensor_tree.heading('pct_mission',   text='% Mission Time')
        self._sensor_tree.column('sensor',        width=80,  anchor='center')
        self._sensor_tree.column('times_enabled', width=100, anchor='center')
        self._sensor_tree.column('total_duration', width=110, anchor='center')
        self._sensor_tree.column('pct_mission',   width=110, anchor='center')
        self._sensor_tree.grid(row=0, column=0, sticky='nsew', padx=4, pady=4)

        # ---- Section B: Time to Detect / Engage ----------------------
        t2e_lf = ttk.LabelFrame(outer, text='Time to Detect / Engage (per target)')
        t2e_lf.grid(row=1, column=0, padx=6, pady=2, sticky='nsew')
        t2e_lf.columnconfigure(0, weight=1)

        t2e_cols = ('rat_id', 'detected_at', 'zone3_at', 'engage_at',
                    'detect_to_zone3', 'detect_to_engage')
        self._t2e_tree = ttk.Treeview(
            t2e_lf, columns=t2e_cols, show='headings', height=5
        )
        self._t2e_tree.heading('rat_id',          text='Target')
        self._t2e_tree.heading('detected_at',     text='First Detected')
        self._t2e_tree.heading('zone3_at',        text='Reached Zone 3')
        self._t2e_tree.heading('engage_at',       text='Engage Cmd')
        self._t2e_tree.heading('detect_to_zone3', text='Detect→Z3')
        self._t2e_tree.heading('detect_to_engage', text='Detect→Engage')
        self._t2e_tree.column('rat_id',           width=80,  anchor='center')
        self._t2e_tree.column('detected_at',      width=105, anchor='center')
        self._t2e_tree.column('zone3_at',         width=105, anchor='center')
        self._t2e_tree.column('engage_at',        width=105, anchor='center')
        self._t2e_tree.column('detect_to_zone3',  width=90,  anchor='center')
        self._t2e_tree.column('detect_to_engage', width=110, anchor='center')

        t2e_scroll = ttk.Scrollbar(t2e_lf, orient='vertical', command=self._t2e_tree.yview)
        self._t2e_tree.configure(yscrollcommand=t2e_scroll.set)
        self._t2e_tree.grid(row=0, column=0, sticky='nsew', padx=(4, 0), pady=4)
        t2e_scroll.grid(row=0, column=1, sticky='ns', pady=4)

        # ---- F2T2EA Event Rates & Durations (stub) --------
        c_lf = ttk.LabelFrame(outer, text='F2T2EA Event Rates & Durations')
        c_lf.grid(row=2, column=0, padx=6, pady=2, sticky='nsew')
        ttk.Label(
            c_lf,
            text='[Awaiting Effector Integration]',
            foreground='gray',
        ).pack(padx=8, pady=6, anchor='w')

        # ---- Identification Accuracy (stub) ---------------
        d_lf = ttk.LabelFrame(outer, text='Identification Accuracy')
        d_lf.grid(row=3, column=0, padx=6, pady=2, sticky='nsew')
        ttk.Label(
            d_lf,
            text='[Awaiting Effector Integration]',
            foreground='gray',
        ).pack(padx=8, pady=6, anchor='w')

        # ---- Engagement Success Rate (stub) ---------------
        e_lf = ttk.LabelFrame(outer, text='Engagement Success Rate')
        e_lf.grid(row=4, column=0, padx=6, pady=2, sticky='nsew')
        ttk.Label(
            e_lf,
            text='[Awaiting Effector Integration]',
            foreground='gray',
        ).pack(padx=8, pady=6, anchor='w')

        # ---- Losses per Target (stub) ---------------------
        f_lf = ttk.LabelFrame(outer, text='Losses per Target')
        f_lf.grid(row=5, column=0, padx=6, pady=2, sticky='nsew')
        ttk.Label(
            f_lf,
            text='[Awaiting Effector Integration]',
            foreground='gray',
        ).pack(padx=8, pady=6, anchor='w')

        # ---- Buttons -------------------------------------------------
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=6, column=0, padx=6, pady=(2, 6), sticky='ew')

        ttk.Button(btn_frame, text='Refresh', command=self.refresh).pack(
            side='left', padx=(0, 6)
        )
        ttk.Button(btn_frame, text='Export CSV', command=self._export_csv).pack(
            side='left'
        )

        # Start the auto-refresh loop
        self._schedule_refresh()

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_sensor_table(self):
        self._sensor_tree.delete(*self._sensor_tree.get_children())
        if self._db is None:
            return
        durations = self._db.get_sensor_durations()
        labels = {'lidar': 'LiDAR', 'rf': 'RF', 'acoustic': 'Acoustic'}
        for key, label in labels.items():
            d = durations.get(key, {})
            self._sensor_tree.insert('', 'end', values=(
                label,
                d.get('times_enabled', 0),
                _fmt_duration(d.get('total_seconds')),
                f"{d.get('pct_mission', 0.0):.1f}%",
            ))

    def _populate_t2e_table(self):
        self._t2e_tree.delete(*self._t2e_tree.get_children())
        if self._db is None:
            return
        rows = self._db.get_time_to_engage()
        for r in rows:
            self._t2e_tree.insert('', 'end', values=(
                r['rat_id'],
                _fmt_ts(r['detected_at']),
                _fmt_ts(r['zone3_at']),
                _fmt_ts(r['engage_at']),
                _fmt_elapsed(r['detect_to_zone3_s']),
                _fmt_elapsed(r['detect_to_engage_s']),
            ))

    # ------------------------------------------------------------------
    # Auto-refresh
    # ------------------------------------------------------------------

    def _schedule_refresh(self):
        self._refresh_job = self.after(self._REFRESH_MS, self._auto_refresh)

    def _auto_refresh(self):
        self.refresh()
        self._schedule_refresh()

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def _export_csv(self):
        if self._db is None:
            return

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
        os.makedirs(export_dir, exist_ok=True)
        path = os.path.abspath(
            os.path.join(export_dir, f'analytics_export_{ts}.csv')
        )

        durations = self._db.get_sensor_durations()
        t2e_rows  = self._db.get_time_to_engage()

        with open(path, 'w', newline='') as f:
            w = csv.writer(f)

            w.writerow(['Section A — Sensor Mode Usage'])
            w.writerow(['Sensor', 'Times Enabled', 'Total Duration (s)', '% Mission Time'])
            for key, label in (('lidar', 'LiDAR'), ('rf', 'RF'), ('acoustic', 'Acoustic')):
                d = durations.get(key, {})
                w.writerow([
                    label,
                    d.get('times_enabled', 0),
                    f"{d.get('total_seconds', 0.0):.1f}",
                    f"{d.get('pct_mission', 0.0):.1f}",
                ])

            w.writerow([])
            w.writerow(['Section B — Time to Detect / Engage'])
            w.writerow([
                'Target', 'First Detected', 'Reached Zone 3', 'Engage Cmd',
                'Detect→Z3 (s)', 'Detect→Engage (s)',
            ])
            for r in t2e_rows:
                w.writerow([
                    r['rat_id'],
                    _fmt_ts(r['detected_at']),
                    _fmt_ts(r['zone3_at']),
                    _fmt_ts(r['engage_at']),
                    f"{r['detect_to_zone3_s']:.1f}"  if r['detect_to_zone3_s']  is not None else '---',
                    f"{r['detect_to_engage_s']:.1f}" if r['detect_to_engage_s'] is not None else '---',
                ])

        print(f"Analytics exported to {path}")
