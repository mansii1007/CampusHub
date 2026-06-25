"""
timetable.py
============
Timetable management module for CampusHub.

Provides the TimetableView frame with:
    - Department-wise timetable
    - Semester-wise timetable
    - Faculty-wise timetable
    - Add / remove slots with room allocation
"""

import tkinter as tk
from tkinter import ttk, messagebox

from database import db
import theme


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DEFAULT_SLOTS = ["09:00 - 10:00", "10:00 - 11:00", "11:30 - 12:30",
                 "13:30 - 14:30", "14:30 - 15:30", "15:45 - 16:45"]


class TimetableView(tk.Frame):
    """Admin / viewer panel for class schedules."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="🗓  Timetable Management",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Department / semester / faculty-wise class schedules",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        # Filters
        filters = tk.Frame(self, bg=theme.BG_PRIMARY)
        filters.pack(fill="x", padx=30, pady=16)

        tk.Label(filters, text="View by:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.mode = ttk.Combobox(filters, values=["Department", "Semester", "Faculty"],
                                 state="readonly", width=14)
        self.mode.set("Department")
        self.mode.pack(side="left", padx=4)
        self.mode.bind("<<ComboboxSelected>>", self._update_value_combo)

        tk.Label(filters, text="Value:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.value_combo = ttk.Combobox(filters, state="readonly", width=20)
        self.value_combo.pack(side="left", padx=4)
        self._update_value_combo()

        theme.RoundedButton(filters, "🔍 Load", self.load_timetable,
                            width=80, height=34).pack(side="left", padx=8)
        if self.role == "admin":
            theme.RoundedButton(filters, "+ Add Slot", self.add_slot,
                                width=100, height=34).pack(side="left", padx=4)
            theme.RoundedButton(filters, "🗑 Clear Filter Slots", self.clear_slots,
                                width=170, height=34, bg=theme.BG_DANGER,
                                hover_bg="#d83b2c").pack(side="left", padx=4)

        # Timetable grid
        self.grid_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        self.grid_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self.load_timetable()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _update_value_combo(self, _=None):
        mode = self.mode.get()
        if mode == "Department":
            vals = [d["name"] for d in db.fetch_all("SELECT name FROM departments")] or ["Computer Science"]
        elif mode == "Semester":
            vals = [str(i) for i in range(1, 9)]
        else:  # Faculty
            vals = [f["faculty_id"] for f in db.fetch_all("SELECT faculty_id FROM faculty")] or ["FAC001"]
        self.value_combo["values"] = vals
        if vals:
            self.value_combo.set(vals[0])

    def _current_filter(self):
        """Return (mode, value) for the active filter selection."""
        return self.mode.get(), self.value_combo.get()

    # -------------------------------------------------------------------------
    # Load timetable
    # -------------------------------------------------------------------------
    def load_timetable(self):
        """Render the timetable as a Day x Slot grid for the active filter."""
        for w in self.grid_frame.winfo_children():
            w.destroy()

        mode, value = self._current_filter()
        if not value:
            return

        # Fetch matching rows
        if mode == "Department":
            rows = db.fetch_all(
                "SELECT day, time_slot, subject, faculty_id, room FROM timetable "
                "WHERE department = ? ORDER BY rowid", (value,))
        elif mode == "Semester":
            rows = db.fetch_all(
                "SELECT day, time_slot, subject, faculty_id, room FROM timetable "
                "WHERE semester = ? ORDER BY rowid", (int(value),))
        else:  # Faculty
            rows = db.fetch_all(
                "SELECT day, time_slot, subject, faculty_id, room FROM timetable "
                "WHERE faculty_id = ? ORDER BY rowid", (value,))

        # Build lookup: (day, slot) -> "Subject\nFaculty · Room"
        lookup = {(r["day"], r["time_slot"]): r for r in rows}

        # Header row
        tk.Label(self.grid_frame, text=f"Timetable — {mode}: {value}",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_HEADING).grid(row=0, column=0, columnspan=len(DEFAULT_SLOTS) + 1,
                                               pady=(0, 8))

        # Top-left corner
        corner = tk.Label(self.grid_frame, text="Day / Time", bg=theme.BG_ACCENT,
                          fg=theme.FG_PRIMARY, font=theme.FONT_BODY_BOLD,
                          width=12, height=2, relief="ridge")
        corner.grid(row=1, column=0, sticky="nsew")
        for j, slot in enumerate(DEFAULT_SLOTS):
            tk.Label(self.grid_frame, text=slot, bg=theme.BG_ACCENT,
                     fg=theme.FG_PRIMARY, font=theme.FONT_SMALL,
                     width=12, height=2, relief="ridge").grid(
                row=1, column=j + 1, sticky="nsew")

        # Body
        for i, day in enumerate(DAYS):
            tk.Label(self.grid_frame, text=day, bg=theme.BG_CARD,
                     fg=theme.FG_PRIMARY, font=theme.FONT_BODY_BOLD,
                     width=12, height=3, relief="ridge").grid(
                row=i + 2, column=0, sticky="nsew")
            for j, slot in enumerate(DEFAULT_SLOTS):
                entry = lookup.get((day, slot))
                if entry:
                    text = f"{entry['subject']}\n{entry.get('faculty_id','')}\nRoom {entry.get('room','—')}"
                    bg, fg = theme.BG_SUCCESS, theme.FG_PRIMARY
                else:
                    text = "—"
                    bg, fg = theme.BG_CARD, theme.FG_MUTED
                tk.Label(self.grid_frame, text=text, bg=bg, fg=fg,
                         font=theme.FONT_SMALL, width=14, height=3,
                         relief="ridge", justify="center").grid(
                    row=i + 2, column=j + 1, sticky="nsew")

        # Stretch columns
        for j in range(len(DEFAULT_SLOTS) + 1):
            self.grid_frame.grid_columnconfigure(j, weight=1)

    # -------------------------------------------------------------------------
    # Add / clear
    # -------------------------------------------------------------------------
    def add_slot(self):
        win = tk.Toplevel(self)
        win.title("Add Timetable Slot")
        win.geometry("400x460")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 400, 460)
        tk.Label(win, text="➕ Add Timetable Slot", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack(pady=(18, 14))

        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        depts = [d["name"] for d in db.fetch_all("SELECT name FROM departments")] or ["Computer Science"]
        faculty = [f["faculty_id"] for f in db.fetch_all("SELECT faculty_id FROM faculty")] or ["FAC001"]
        subjects = [c["course_name"] for c in db.fetch_all("SELECT course_name FROM courses")] or ["General"]

        fields = {}
        items = [("department", "Department", depts),
                 ("semester", "Semester", [str(i) for i in range(1, 9)]),
                 ("day", "Day", DAYS),
                 ("time_slot", "Time Slot", DEFAULT_SLOTS),
                 ("subject", "Subject", subjects),
                 ("faculty_id", "Faculty", faculty)]
        for i, (key, label, vals) in enumerate(items):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            cb = ttk.Combobox(form, values=vals, state="readonly", width=22)
            cb.set(vals[0])
            cb.grid(row=i, column=1, pady=6, padx=8)
            fields[key] = cb

        room_e = None
        tk.Label(form, text="Room", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
            row=len(items), column=0, sticky="w", pady=6)
        room_e = tk.Entry(form, width=24, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                          relief="flat", bd=6, font=theme.FONT_BODY,
                          highlightthickness=1, highlightbackground=theme.BORDER_COLOR,
                          highlightcolor=theme.BG_ACCENT)
        room_e.grid(row=len(items), column=1, pady=6, padx=8)
        room_e.insert(0, "101")

        def save():
            data = {k: w.get() for k, w in fields.items()}
            data["room"] = room_e.get().strip() or "—"
            try:
                data["semester"] = int(data["semester"])
            except ValueError:
                data["semester"] = 1
            db.execute(
                "INSERT INTO timetable (department, semester, day, time_slot, "
                "subject, faculty_id, room) VALUES (?,?,?,?,?,?,?)",
                (data["department"], data["semester"], data["day"],
                 data["time_slot"], data["subject"], data["faculty_id"], data["room"]),
            )
            db.log_activity(f"Added slot {data['subject']} ({data['day']} {data['time_slot']})")
            messagebox.showinfo("Success", "Slot added.", parent=win)
            win.destroy()
            self.load_timetable()

        theme.RoundedButton(win, "💾 Save", command=save,
                            width=180, height=42).pack(pady=18)

    def clear_slots(self):
        """Delete all timetable slots matching the active filter."""
        mode, value = self._current_filter()
        if not value:
            return
        if not messagebox.askyesno("Confirm",
                                   f"Delete all timetable slots for {mode} = {value}?"):
            return
        if mode == "Department":
            db.execute("DELETE FROM timetable WHERE department = ?", (value,))
        elif mode == "Semester":
            db.execute("DELETE FROM timetable WHERE semester = ?", (int(value),))
        else:
            db.execute("DELETE FROM timetable WHERE faculty_id = ?", (value,))
        db.log_activity(f"Cleared timetable slots for {mode}={value}")
        self.load_timetable()
