"""
marks.py
========
Marks & grading module for CampusHub.

Provides the MarksView frame with:
    - Upload / edit marks (internal, practical, semester exam)
    - Automatic grade calculation (O / A+ / A / B+ / ... / F)
    - Automatic SGPA per semester and CGPA (weighted average of SGPAs)
    - Marksheet preview per student

Grading scale (out of 100, weight: internal 30% + practical 20% + exam 50%):
    >=90 -> O   (10 points)
    >=80 -> A+  (9)
    >=70 -> A   (8)
    >=60 -> B+  (7)
    >=50 -> B   (6)
    >=40 -> C   (5)
    <40  -> F   (0)
"""

import tkinter as tk
from tkinter import ttk, messagebox

from database import db
import theme


# -----------------------------------------------------------------------------
# Grading helpers
# -----------------------------------------------------------------------------
def compute_percentage(internal: float, practical: float, semester_exam: float) -> float:
    """
    Combine internal / practical / semester marks into a percentage out of 100.

    The three components are already scaled to sum to 100
    (Internal /30  +  Practical /20  +  Semester /50  =  /100), so the
    overall percentage is simply their sum, capped to 100.
    """
    return min(100.0, (internal or 0) + (practical or 0) + (semester_exam or 0))


def compute_grade(pct: float) -> tuple:
    """Return (grade_letter, grade_point) for a given percentage."""
    scale = [
        (90, "O", 10), (80, "A+", 9), (70, "A", 8), (60, "B+", 7),
        (50, "B", 6), (40, "C", 5), (0, "F", 0),
    ]
    for threshold, letter, point in scale:
        if pct >= threshold:
            return letter, point
    return "F", 0


def compute_sgpa(student_id: str, semester: int = None) -> float:
    """
    Compute SGPA for a student using grade points × credits / total credits.
    Falls back to a simple grade-point average when credits are unavailable.
    """
    rows = db.fetch_all(
        "SELECT m.subject, m.grade, m.semester_exam, m.internal, m.practical, "
        "c.credits FROM marks m "
        "LEFT JOIN courses c ON c.course_name = m.subject "
        "WHERE m.student_id = ?", (student_id,)
    )
    if not rows:
        return 0.0
    total_points = 0.0
    total_credits = 0.0
    for r in rows:
        pct = compute_percentage(r.get("internal") or 0, r.get("practical") or 0,
                                 r.get("semester_exam") or 0)
        _, point = compute_grade(pct)
        credits = r.get("credits") or 3
        total_points += point * credits
        total_credits += credits
    return round(total_points / total_credits, 2) if total_credits else 0.0


def compute_cgpa(student_id: str) -> float:
    """
    Compute CGPA as the average of SGPAs across all semesters that have marks.
    (Simple average; replace with weighted logic if semester-wise data grows.)
    """
    rows = db.fetch_all(
        "SELECT s.semester, AVG(m.internal + m.practical + m.semester_exam) AS avg_pct "
        "FROM marks m JOIN students s ON s.roll_no = m.student_id "
        "WHERE m.student_id = ? GROUP BY s.semester", (student_id,)
    )
    if not rows:
        return 0.0
    points = []
    for r in rows:
        _, pt = compute_grade(r["avg_pct"] or 0)
        points.append(pt)
    return round(sum(points) / len(points), 2) if points else 0.0


# -----------------------------------------------------------------------------
# View
# -----------------------------------------------------------------------------
class MarksView(tk.Frame):
    """Admin / faculty panel for marks entry and grade computation."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="📊  Marks & Grading",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Upload marks; grades, SGPA and CGPA are computed automatically",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)
        self._tab_upload(nb)
        self._tab_marksheet(nb)

    # -------------------------------------------------------------------------
    # Upload tab
    # -------------------------------------------------------------------------
    def _tab_upload(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Upload Marks  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)

        tk.Label(controls, text="Student:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        students = [f"{s['roll_no']} - {s['name']}"
                    for s in db.fetch_all("SELECT roll_no, name FROM students ORDER BY roll_no")]
        self.stu_combo = ttk.Combobox(controls, values=students, state="readonly", width=28)
        self.stu_combo.pack(side="left", padx=4)

        tk.Label(controls, text="Subject:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        subjects = [c["course_name"] for c in db.fetch_all("SELECT course_name FROM courses")] or ["General"]
        self.subj_combo = ttk.Combobox(controls, values=subjects, state="readonly", width=22)
        self.subj_combo.pack(side="left", padx=4)

        # Marks inputs
        inputs = tk.Frame(tab, bg=theme.BG_PRIMARY)
        inputs.pack(pady=12)
        self.entries = {}
        for i, (key, label, mx) in enumerate([("internal", "Internal (/30)", 30),
                                              ("practical", "Practical (/20)", 20),
                                              ("semester_exam", "Semester Exam (/50)", 50)]):
            tk.Label(inputs, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_BODY).grid(
                row=0, column=i, padx=10)
            e = tk.Entry(inputs, width=8, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                         relief="flat", bd=6, font=theme.FONT_BODY,
                         highlightthickness=1, highlightbackground=theme.BORDER_COLOR,
                         highlightcolor=theme.BG_ACCENT, justify="center")
            e.insert(0, "0")
            e.grid(row=1, column=i, padx=10, pady=6)
            self.entries[key] = e

        theme.RoundedButton(tab, "💾 Save Marks", self.save_marks,
                            width=160, height=40).pack(pady=8)

        # Live preview of grade
        self.preview = tk.Label(tab, text="", bg=theme.BG_PRIMARY,
                                fg=theme.BG_ACCENT, font=theme.FONT_HEADING)
        self.preview.pack(pady=4)
        for e in self.entries.values():
            e.bind("<KeyRelease>", self._update_preview)

    def _update_preview(self, _=None):
        try:
            i = float(self.entries["internal"].get() or 0)
            p = float(self.entries["practical"].get() or 0)
            s = float(self.entries["semester_exam"].get() or 0)
            pct = compute_percentage(i, p, s)
            grade, point = compute_grade(pct)
            self.preview.config(text=f"Percentage: {pct:.1f}%   Grade: {grade}  ({point} pts)")
        except ValueError:
            self.preview.config(text="Enter valid numbers")

    def save_marks(self):
        sel = self.stu_combo.get()
        if not sel:
            messagebox.showwarning("Validation", "Please select a student.")
            return
        student_id = sel.split(" - ")[0]
        subject = self.subj_combo.get()
        try:
            internal = float(self.entries["internal"].get() or 0)
            practical = float(self.entries["practical"].get() or 0)
            semester_exam = float(self.entries["semester_exam"].get() or 0)
        except ValueError:
            messagebox.showwarning("Validation", "Marks must be numeric.")
            return
        if not (0 <= internal <= 30 and 0 <= practical <= 20 and 0 <= semester_exam <= 50):
            messagebox.showwarning("Validation",
                                   "Ranges: Internal 0-30, Practical 0-20, Semester 0-50.")
            return
        pct = compute_percentage(internal, practical, semester_exam)
        grade, _ = compute_grade(pct)

        # Upsert: replace existing record for student+subject
        existing = db.fetch_one(
            "SELECT id FROM marks WHERE student_id = ? AND subject = ?",
            (student_id, subject)
        )
        if existing:
            db.execute(
                "UPDATE marks SET internal=?, practical=?, semester_exam=?, grade=? "
                "WHERE student_id=? AND subject=?",
                (internal, practical, semester_exam, grade, student_id, subject),
            )
        else:
            db.execute(
                "INSERT INTO marks (student_id, subject, internal, practical, "
                "semester_exam, grade) VALUES (?,?,?,?,?,?)",
                (student_id, subject, internal, practical, semester_exam, grade),
            )

        # Recompute and store CGPA on the student record
        cgpa = compute_cgpa(student_id)
        db.execute("UPDATE students SET cgpa = ? WHERE roll_no = ?", (cgpa, student_id))
        db.log_activity(f"Saved marks for {student_id} - {subject} ({grade})")
        messagebox.showinfo("Success",
                            f"Marks saved.\nPercentage: {pct:.1f}%  Grade: {grade}\n"
                            f"Updated CGPA: {cgpa}")

    # -------------------------------------------------------------------------
    # Marksheet tab
    # -------------------------------------------------------------------------
    def _tab_marksheet(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Marksheet  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)
        tk.Label(controls, text="Student:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        students = [f"{s['roll_no']} - {s['name']}"
                    for s in db.fetch_all("SELECT roll_no, name FROM students ORDER BY roll_no")]
        self.mk_stu = ttk.Combobox(controls, values=students, state="readonly", width=28)
        self.mk_stu.pack(side="left", padx=4)
        theme.RoundedButton(controls, "🔍 Generate", self.generate_marksheet,
                            width=110, height=34).pack(side="left", padx=8)

        # Marksheet card
        self.sheet = tk.Frame(tab, bg=theme.BG_CARD,
                              highlightbackground=theme.BORDER_COLOR,
                              highlightthickness=1)
        self.sheet.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        tk.Label(self.sheet, text="Select a student and click Generate to view marksheet",
                 bg=theme.BG_CARD, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(pady=40)

    def generate_marksheet(self):
        sel = self.mk_stu.get()
        if not sel:
            messagebox.showwarning("Validation", "Please select a student.")
            return
        student_id = sel.split(" - ")[0]
        student = db.fetch_one("SELECT * FROM students WHERE roll_no = ?", (student_id,))
        marks = db.fetch_all("SELECT * FROM marks WHERE student_id = ?", (student_id,))
        cgpa = compute_cgpa(student_id)

        # Clear sheet
        for w in self.sheet.winfo_children():
            w.destroy()

        # Header
        header = tk.Frame(self.sheet, bg=theme.BG_ACCENT)
        header.pack(fill="x")
        tk.Label(header, text="🎓  CampusHub — Official Marksheet",
                 bg=theme.BG_ACCENT, fg=theme.FG_PRIMARY,
                 font=theme.FONT_SUBTITLE).pack(pady=10)

        info = tk.Frame(self.sheet, bg=theme.BG_CARD)
        info.pack(fill="x", padx=30, pady=14)
        info_pairs = [("Name", student.get("name")), ("Roll No", student_id),
                      ("Department", student.get("department")),
                      ("Semester", student.get("semester"))]
        for i, (k, v) in enumerate(info_pairs):
            tk.Label(info, text=f"{k}: ", bg=theme.BG_CARD, fg=theme.FG_MUTED,
                     font=theme.FONT_BODY_BOLD).grid(row=0, column=i * 2, sticky="w", padx=4)
            tk.Label(info, text=str(v or "—"), bg=theme.BG_CARD, fg=theme.FG_PRIMARY,
                     font=theme.FONT_BODY).grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 16))

        # Subjects table
        cols = ("subject", "internal", "practical", "exam", "pct", "grade")
        tree = ttk.Treeview(self.sheet, columns=cols, show="headings", height=10)
        for c, t, w in [("subject", "Subject", 200), ("internal", "Internal", 80),
                        ("practical", "Practical", 80), ("exam", "Exam", 80),
                        ("pct", "% ", 70), ("grade", "Grade", 70)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=30, pady=(0, 14))
        for m in marks:
            pct = compute_percentage(m["internal"], m["practical"], m["semester_exam"])
            tree.insert("", "end", values=(
                m["subject"], m["internal"], m["practical"], m["semester_exam"],
                f"{pct:.1f}", m["grade"],
            ))

        if not marks:
            tree.insert("", "end", values=("No marks recorded", "", "", "", "", ""))

        # Result footer
        footer = tk.Frame(self.sheet, bg=theme.BG_CARD)
        footer.pack(fill="x", padx=30, pady=(0, 18))
        tk.Label(footer, text=f"CGPA: ", bg=theme.BG_CARD, fg=theme.FG_MUTED,
                 font=theme.FONT_HEADING).pack(side="left")
        tk.Label(footer, text=f"{cgpa} / 10", bg=theme.BG_CARD, fg=theme.BG_SUCCESS,
                 font=theme.FONT_HEADING).pack(side="left")
        tk.Label(footer, text=f"Result: {'PASS' if cgpa >= 5 else 'FAIL'}",
                 bg=theme.BG_CARD,
                 fg=theme.BG_SUCCESS if cgpa >= 5 else theme.BG_DANGER,
                 font=theme.FONT_HEADING).pack(side="right")
