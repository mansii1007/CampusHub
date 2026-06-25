"""
dashboard.py
============
Dashboard module for CampusHub.

Renders the landing screen shown right after login.  It contains:
    - A grid of statistics cards (students, faculty, departments,
      attendance %, average CGPA, fee collection, library books)
    - A "recent activities" feed
    - An optional bar chart (drawn with the Canvas, no external libs)

`DashboardView` is a plain Tk frame so it can be embedded inside the
main app shell's content area.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from database import db
import theme


class DashboardView(tk.Frame):
    """The dashboard panel shown after login."""

    def __init__(self, parent, role="admin", ref_id="", username=""):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self.ref_id = ref_id
        self.username = username
        self._build_ui()
        self.load_stats()

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=theme.BG_PRIMARY)
        header.pack(fill="x", padx=30, pady=(26, 6))

        greeting = "Welcome back" if self.role != "student" else "Hello"
        name = self._display_name()
        tk.Label(header, text=f"{greeting}, {name} 👋",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(side="left")
        tk.Label(header, text=datetime.now().strftime("%A, %d %B %Y"),
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(side="right")

        tk.Label(self, text="Overview of your campus at a glance",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        # Stats grid
        self.stats_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        self.stats_frame.pack(fill="x", padx=30, pady=(18, 10))

        # Bottom row: chart + activity
        bottom = tk.Frame(self, bg=theme.BG_PRIMARY)
        bottom.pack(fill="both", expand=True, padx=30, pady=(6, 20))

        # Recent activity card
        activity_card = tk.Frame(bottom, bg=theme.BG_CARD,
                                 highlightbackground=theme.BORDER_COLOR,
                                 highlightthickness=1)
        activity_card.pack(side="right", fill="both", expand=True)
        tk.Label(activity_card, text="🕒  Recent Activities",
                 bg=theme.BG_CARD, fg=theme.FG_PRIMARY,
                 font=theme.FONT_HEADING).pack(anchor="w", padx=18, pady=(16, 8))

        self.activity_list = tk.Frame(activity_card, bg=theme.BG_CARD)
        self.activity_list.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        # Chart card
        chart_card = tk.Frame(bottom, bg=theme.BG_CARD,
                              highlightbackground=theme.BORDER_COLOR,
                              highlightthickness=1, width=520)
        chart_card.pack(side="left", fill="both", expand=True, padx=(0, 14))
        chart_card.pack_propagate(False)
        tk.Label(chart_card, text="📊  Students per Department",
                 bg=theme.BG_CARD, fg=theme.FG_PRIMARY,
                 font=theme.FONT_HEADING).pack(anchor="w", padx=18, pady=(16, 8))
        self.chart_canvas = tk.Canvas(chart_card, bg=theme.BG_CARD,
                                      highlightthickness=0, height=240)
        self.chart_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 14))

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------
    def load_stats(self):
        """Refresh every card and widget with the latest DB figures."""
        # Wipe existing stat cards
        for w in self.stats_frame.winfo_children():
            w.destroy()

        stats = self._gather_stats()
        pairs = [theme.CARD_COLORS[i % len(theme.CARD_COLORS)] for i in range(len(stats))]

        # Lay out in 2 rows x 4 columns
        for i, (title, value, subtitle) in enumerate(stats):
            card = theme.StatCard(self.stats_frame, title=title, value=value,
                                  subtitle=subtitle, color_pair=pairs[i])
            row = i // 4
            col = i % 4
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.stats_frame.grid_columnconfigure(col, weight=1)

        self._load_activity()
        self._draw_chart()

    def _gather_stats(self):
        """Return a list of (title, value, subtitle) tuples from the DB."""
        total_students = db.fetch_one("SELECT COUNT(*) AS c FROM students")["c"]
        total_faculty = db.fetch_one("SELECT COUNT(*) AS c FROM faculty")["c"]
        total_depts = db.fetch_one("SELECT COUNT(*) AS c FROM departments")["c"]
        total_books = db.fetch_one("SELECT COUNT(*) AS c FROM library")["c"]

        # Attendance percentage
        att = db.fetch_one(
            "SELECT "
            "SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS p, "
            "COUNT(*) AS t FROM attendance"
        )
        att_pct = round((att["p"] / att["t"] * 100), 1) if att and att["t"] else 0.0

        # Average CGPA
        cgpa_row = db.fetch_one("SELECT AVG(cgpa) AS a FROM students")
        avg_cgpa = round(cgpa_row["a"], 2) if cgpa_row and cgpa_row["a"] else 0.0

        # Fee collection
        fee_row = db.fetch_one("SELECT SUM(amount) AS s FROM fees WHERE status='Paid'")
        fee_total = fee_row["s"] if fee_row and fee_row["s"] else 0.0

        pending_fees = db.fetch_one(
            "SELECT SUM(amount) AS s FROM fees WHERE status != 'Paid'"
        )
        pending = pending_fees["s"] if pending_fees and pending_fees["s"] else 0.0

        return [
            ("Total Students", total_students, "Enrolled"),
            ("Total Faculty", total_faculty, "Teaching staff"),
            ("Departments", total_depts, "Active"),
            ("Library Books", total_books, "In catalog"),
            ("Attendance %", att_pct, "Overall"),
            ("Average CGPA", avg_cgpa, "Across students"),
            ("Fee Collected", f"₹{fee_total:,.0f}", "Paid"),
            ("Pending Fees", f"₹{pending:,.0f}", "Outstanding"),
        ]

    def _load_activity(self):
        """Populate the recent activity feed."""
        for w in self.activity_list.winfo_children():
            w.destroy()
        rows = db.fetch_all(
            "SELECT activity, created_at FROM activity_log "
            "ORDER BY id DESC LIMIT 8"
        )
        if not rows:
            tk.Label(self.activity_list, text="No recent activity",
                     bg=theme.BG_CARD, fg=theme.FG_MUTED,
                     font=theme.FONT_BODY).pack(pady=20)
            return

        for row in rows:
            item = tk.Frame(self.activity_list, bg=theme.BG_CARD)
            item.pack(fill="x", pady=4)
            dot = tk.Label(item, text="●", bg=theme.BG_CARD,
                           fg=theme.BG_ACCENT, font=("Segoe UI", 8))
            dot.pack(side="left")
            tk.Label(item, text=row["activity"], bg=theme.BG_CARD,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL,
                     anchor="w").pack(side="left", padx=6)
            tk.Label(item, text=(row.get("created_at") or "")[-8:],
                     bg=theme.BG_CARD, fg=theme.FG_MUTED,
                     font=("Segoe UI", 8)).pack(side="right")

    def _draw_chart(self):
        """Draw a simple bar chart of students per department."""
        c = self.chart_canvas
        c.delete("all")
        rows = db.fetch_all(
            "SELECT department, COUNT(*) AS c FROM students "
            "GROUP BY department ORDER BY c DESC"
        )
        if not rows:
            c.create_text(200, 120, text="No student data yet",
                          fill=theme.FG_MUTED, font=theme.FONT_BODY)
            return

        c.update_idletasks()
        w = max(c.winfo_width(), 400)
        h = max(c.winfo_height(), 220)
        padding = 50
        chart_w = w - padding * 2
        chart_h = h - 70
        max_val = max(r["c"] for r in rows)
        bar_w = min(50, chart_w // (len(rows) + 1))

        for i, row in enumerate(rows):
            val = row["c"]
            bh = (val / max_val) * chart_h if max_val else 0
            x0 = padding + i * (bar_w + 18)
            y0 = h - 40 - bh
            color = theme.CARD_COLORS[i % len(theme.CARD_COLORS)][0]
            c.create_rectangle(x0, y0, x0 + bar_w, h - 40, fill=color, outline="")
            c.create_text(x0 + bar_w / 2, y0 - 10, text=str(val),
                          fill=theme.FG_PRIMARY, font=("Segoe UI", 9, "bold"))
            label = row["department"] or "N/A"
            if len(label) > 10:
                label = label[:9] + "…"
            c.create_text(x0 + bar_w / 2, h - 25, text=label,
                          fill=theme.FG_MUTED, font=("Segoe UI", 8),
                          angle=0)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _display_name(self):
        if self.role == "admin":
            return "Administrator"
        if self.role == "faculty":
            row = db.fetch_one("SELECT name FROM faculty WHERE faculty_id = ?",
                               (self.ref_id,))
            return row["name"] if row else self.username
        if self.role == "student":
            row = db.fetch_one("SELECT name FROM students WHERE roll_no = ?",
                               (self.ref_id,))
            return row["name"] if row else self.username
        return self.username
