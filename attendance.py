"""
attendance.py
=============
Attendance management module for CampusHub.

Provides the AttendanceView frame with:
    - Mark Attendance (per date & subject, with quick present/absent toggles)
    - Daily Attendance view
    - Monthly Attendance view
    - Attendance percentage per student
    - Defaulter list (students below threshold)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

from database import db
import theme


class AttendanceView(tk.Frame):
    """Admin / faculty panel for attendance operations."""

    def __init__(self, parent, role="admin", faculty_dept=None):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self.faculty_dept = faculty_dept
        self._build_ui()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------
    def _build_ui(self):
        tk.Label(self, text="📅  Attendance Management",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Mark attendance, view reports and identify defaulters",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)
        self._tab_mark(nb)
        self._tab_daily(nb)
        self._tab_monthly(nb)
        self._tab_percentage(nb)
        self._tab_defaulters(nb)

    # -------------------------------------------------------------------------
    # Tab: Mark attendance
    # -------------------------------------------------------------------------
    def _tab_mark(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Mark Attendance  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)

        tk.Label(controls, text="Department:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).grid(row=0, column=0, padx=4)
        depts = [d["name"] for d in db.fetch_all("SELECT name FROM departments")] or ["Computer Science"]
        self.mark_dept = ttk.Combobox(controls, values=depts, state="readonly", width=18)
        self.mark_dept.set(depts[0])
        self.mark_dept.grid(row=0, column=1, padx=4)

        tk.Label(controls, text="Subject:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).grid(row=0, column=2, padx=4)
        subjects = [c["course_name"] for c in db.fetch_all("SELECT course_name FROM courses")] or ["General"]
        self.mark_subject = ttk.Combobox(controls, values=subjects, state="readonly", width=22)
        self.mark_subject.set(subjects[0])
        self.mark_subject.grid(row=0, column=3, padx=4)

        tk.Label(controls, text="Date:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).grid(row=0, column=4, padx=4)
        self.mark_date = tk.Entry(controls, width=12, bg=theme.BG_INPUT,
                                  fg=theme.FG_PRIMARY, relief="flat", bd=5,
                                  highlightthickness=1,
                                  highlightbackground=theme.BORDER_COLOR,
                                  highlightcolor=theme.BG_ACCENT)
        self.mark_date.insert(0, date.today().isoformat())
        self.mark_date.grid(row=0, column=5, padx=4)

        theme.RoundedButton(controls, "Load Students", self._load_mark_list,
                            width=130, height=34).grid(row=0, column=6, padx=8)
        theme.RoundedButton(controls, "💾 Save", self._save_mark,
                            width=80, height=34, bg=theme.BG_SUCCESS,
                            hover_bg="#019875").grid(row=0, column=7, padx=4)

        # Student list for marking
        scroll = tk.Frame(tab, bg=theme.BG_PRIMARY)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.mark_tree = ttk.Treeview(scroll, columns=("roll", "name", "status"),
                                      show="headings", height=14)
        for c, t, w in [("roll", "Roll No", 140), ("name", "Name", 260),
                        ("status", "Status", 160)]:
            self.mark_tree.heading(c, text=t)
            self.mark_tree.column(c, width=w, anchor="center")
        self.mark_tree.pack(fill="both", expand=True, side="left")
        self.mark_tree.bind("<Double-1>", self._toggle_status)
        sb = ttk.Scrollbar(scroll, orient="vertical", command=self.mark_tree.yview)
        self.mark_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tk.Label(tab, text="Tip: double-click a row to toggle Present ⇄ Absent",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_SMALL).pack(pady=(0, 8))

    def _load_mark_list(self):
        """Populate the marking tree with students of the selected department."""
        dept = self.mark_dept.get()
        for r in self.mark_tree.get_children():
            self.mark_tree.delete(r)
        rows = db.fetch_all(
            "SELECT roll_no, name FROM students WHERE department = ? ORDER BY roll_no",
            (dept,)
        )
        for r in rows:
            self.mark_tree.insert("", "end", values=(r["roll_no"], r["name"], "Present"))
        if not rows:
            messagebox.showinfo("Info", f"No students in {dept} department.")

    def _toggle_status(self, _):
        """Switch Present ⇄ Absent for a double-clicked row."""
        sel = self.mark_tree.selection()
        if not sel:
            return
        vals = self.mark_tree.item(sel[0])["values"]
        new_status = "Absent" if vals[2] == "Present" else "Present"
        self.mark_tree.item(sel[0], values=(vals[0], vals[1], new_status))

    def _save_mark(self):
        """Persist the marked attendance rows."""
        subject = self.mark_subject.get()
        att_date = self.mark_date.get().strip()
        if not att_date:
            messagebox.showwarning("Validation", "Please enter a date.")
            return
        rows = self.mark_tree.get_children()
        if not rows:
            messagebox.showwarning("Empty", "Load students first.")
            return
        try:
            # Remove existing marks for that date+subject to avoid duplicates
            db.execute(
                "DELETE FROM attendance WHERE subject = ? AND date = ?",
                (subject, att_date),
            )
            for r in rows:
                vals = self.mark_tree.item(r)["values"]
                db.execute(
                    "INSERT INTO attendance (student_id, subject, date, status) "
                    "VALUES (?,?,?,?)",
                    (str(vals[0]), subject, att_date, vals[2]),
                )
            db.log_activity(f"Saved attendance for {subject} on {att_date}")
            messagebox.showinfo("Success", "Attendance saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -------------------------------------------------------------------------
    # Tab: Daily attendance
    # -------------------------------------------------------------------------
    def _tab_daily(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Daily Report  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)
        tk.Label(controls, text="Date:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.daily_date = tk.Entry(controls, width=14, bg=theme.BG_INPUT,
                                   fg=theme.FG_PRIMARY, relief="flat", bd=5,
                                   highlightthickness=1,
                                   highlightbackground=theme.BORDER_COLOR,
                                   highlightcolor=theme.BG_ACCENT)
        self.daily_date.insert(0, date.today().isoformat())
        self.daily_date.pack(side="left", padx=4)
        theme.RoundedButton(controls, "🔍 View", self._load_daily,
                            width=80, height=34).pack(side="left", padx=8)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        cols = ("roll", "name", "subject", "date", "status")
        self.daily_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("roll", "Roll No", 120), ("name", "Name", 200),
                        ("subject", "Subject", 200), ("date", "Date", 140),
                        ("status", "Status", 100)]:
            self.daily_tree.heading(c, text=t)
            self.daily_tree.column(c, width=w, anchor="center")
        self.daily_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.daily_tree.yview)
        self.daily_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def _load_daily(self):
        d = self.daily_date.get().strip()
        for r in self.daily_tree.get_children():
            self.daily_tree.delete(r)
        rows = db.fetch_all(
            "SELECT a.student_id, s.name, a.subject, a.date, a.status "
            "FROM attendance a LEFT JOIN students s ON s.roll_no = a.student_id "
            "WHERE a.date = ? ORDER BY a.student_id", (d,)
        )
        for r in rows:
            self.daily_tree.insert("", "end", values=(
                r["student_id"], r.get("name", ""), r["subject"],
                r["date"], r["status"],
            ))

    # -------------------------------------------------------------------------
    # Tab: Monthly attendance
    # -------------------------------------------------------------------------
    def _tab_monthly(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Monthly Report  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)
        tk.Label(controls, text="Month (YYYY-MM):", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.month_val = tk.Entry(controls, width=10, bg=theme.BG_INPUT,
                                  fg=theme.FG_PRIMARY, relief="flat", bd=5,
                                  highlightthickness=1,
                                  highlightbackground=theme.BORDER_COLOR,
                                  highlightcolor=theme.BG_ACCENT)
        self.month_val.insert(0, datetime.now().strftime("%Y-%m"))
        self.month_val.pack(side="left", padx=4)
        theme.RoundedButton(controls, "🔍 View", self._load_monthly,
                            width=80, height=34).pack(side="left", padx=8)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        cols = ("roll", "name", "present", "total", "percent")
        self.monthly_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("roll", "Roll No", 130), ("name", "Name", 220),
                        ("present", "Present", 100), ("total", "Total", 100),
                        ("percent", "% ", 100)]:
            self.monthly_tree.heading(c, text=t)
            self.monthly_tree.column(c, width=w, anchor="center")
        self.monthly_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.monthly_tree.yview)
        self.monthly_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def _load_monthly(self):
        m = self.month_val.get().strip()
        for r in self.monthly_tree.get_children():
            self.monthly_tree.delete(r)
        rows = db.fetch_all(
            "SELECT a.student_id, s.name, "
            "SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS p, "
            "COUNT(*) AS t FROM attendance a "
            "LEFT JOIN students s ON s.roll_no = a.student_id "
            "WHERE substr(a.date,1,7) = ? "
            "GROUP BY a.student_id ORDER BY a.student_id", (m,)
        )
        for r in rows:
            pct = round(r["p"] / r["t"] * 100, 1) if r["t"] else 0
            self.monthly_tree.insert("", "end", values=(
                r["student_id"], r.get("name", ""), r["p"], r["t"], f"{pct}%",
            ))

    # -------------------------------------------------------------------------
    # Tab: Attendance percentage
    # -------------------------------------------------------------------------
    def _tab_percentage(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Percentage  ")
        tk.Label(tab, text="Overall attendance percentage by student",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(pady=12)
        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12)
        cols = ("roll", "name", "present", "total", "percent")
        self.pct_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("roll", "Roll No", 130), ("name", "Name", 220),
                        ("present", "Present", 100), ("total", "Total", 100),
                        ("percent", "%", 100)]:
            self.pct_tree.heading(c, text=t)
            self.pct_tree.column(c, width=w, anchor="center")
        self.pct_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.pct_tree.yview)
        self.pct_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._load_percentage()

    def _load_percentage(self):
        for r in self.pct_tree.get_children():
            self.pct_tree.delete(r)
        rows = db.fetch_all(
            "SELECT a.student_id, s.name, "
            "SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS p, "
            "COUNT(*) AS t FROM attendance a "
            "LEFT JOIN students s ON s.roll_no = a.student_id "
            "GROUP BY a.student_id ORDER BY a.student_id"
        )
        for r in rows:
            pct = round(r["p"] / r["t"] * 100, 1) if r["t"] else 0
            self.pct_tree.insert("", "end", values=(
                r["student_id"], r.get("name", ""), r["p"], r["t"], f"{pct}%",
            ))

    # -------------------------------------------------------------------------
    # Tab: Defaulters
    # -------------------------------------------------------------------------
    def _tab_defaulters(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Defaulters  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)
        tk.Label(controls, text="Threshold %:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.thresh = tk.Entry(controls, width=6, bg=theme.BG_INPUT,
                               fg=theme.FG_PRIMARY, relief="flat", bd=5,
                               highlightthickness=1,
                               highlightbackground=theme.BORDER_COLOR,
                               highlightcolor=theme.BG_ACCENT)
        self.thresh.insert(0, "75")
        self.thresh.pack(side="left", padx=4)
        theme.RoundedButton(controls, "🔍 Find", self._load_defaulters,
                            width=80, height=34, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack(side="left", padx=8)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        cols = ("roll", "name", "percent")
        self.def_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("roll", "Roll No", 140), ("name", "Name", 260),
                        ("percent", "Attendance %", 160)]:
            self.def_tree.heading(c, text=t)
            self.def_tree.column(c, width=w, anchor="center")
        self.def_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.def_tree.yview)
        self.def_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def _load_defaulters(self):
        try:
            threshold = float(self.thresh.get())
        except ValueError:
            messagebox.showwarning("Validation", "Threshold must be a number.")
            return
        for r in self.def_tree.get_children():
            self.def_tree.delete(r)
        rows = db.fetch_all(
            "SELECT a.student_id, s.name, "
            "SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)*100.0/COUNT(*) AS pct "
            "FROM attendance a LEFT JOIN students s ON s.roll_no = a.student_id "
            "GROUP BY a.student_id HAVING pct < ? ORDER BY pct", (threshold,)
        )
        for r in rows:
            self.def_tree.insert("", "end", values=(
                r["student_id"], r.get("name", ""), f"{round(r['pct'], 1)}%",
            ))
