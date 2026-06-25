"""
students.py
===========
Student management module for CampusHub.

Provides:
    - StudentsView     : Admin-facing CRUD for students (add / update /
                         delete / search / view all)
    - StudentProfileView : Student-facing personal dashboard (profile,
                         attendance, marks, fees, timetable, library)

ID generation, CSV export and input validation are all handled here.
"""

import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from database import db
import theme


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def generate_student_id() -> str:
    """Generate the next sequential student roll number, e.g. STU001."""
    row = db.fetch_one("SELECT COUNT(*) AS c FROM students")
    count = row["c"] if row else 0
    return f"STU{count + 1:03d}"


def validate_email(email: str) -> bool:
    """Very small email sanity check."""
    return "@" in email and "." in email.split("@")[-1]


# -----------------------------------------------------------------------------
# Admin-facing student management
# -----------------------------------------------------------------------------
class StudentsView(tk.Frame):
    """Admin panel for managing students."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self.selected_roll = None
        self._build_ui()
        self.refresh_table()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------
    def _build_ui(self):
        tk.Label(self, text="👥  Student Management",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Add, update, search and export student records",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        # Action bar
        actions = tk.Frame(self, bg=theme.BG_PRIMARY)
        actions.pack(fill="x", padx=30, pady=14)

        theme.RoundedButton(actions, "+ Add Student", self.open_add_dialog,
                            width=130).pack(side="left", padx=(0, 8))
        theme.RoundedButton(actions, "✎ Update", self.update_selected,
                            width=110, bg=theme.BG_INFO,
                            hover_bg="#3a9fde").pack(side="left", padx=4)
        theme.RoundedButton(actions, "🗑 Delete", self.delete_selected,
                            width=110, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack(side="left", padx=4)
        theme.RoundedButton(actions, "⤓ Export CSV", self.export_csv,
                            width=120, bg=theme.BG_SUCCESS,
                            hover_bg="#019875").pack(side="left", padx=4)
        theme.RoundedButton(actions, "🆔 New ID", self.show_new_id,
                            width=100, bg=theme.BG_WARNING,
                            hover_bg="#d68910").pack(side="left", padx=4)

        # Search bar
        search_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        search_frame.pack(fill="x", padx=30)
        tk.Label(search_frame, text="🔍", bg=theme.BG_PRIMARY,
                 fg=theme.FG_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_table())
        entry = tk.Entry(search_frame, textvariable=self.search_var,
                         bg=theme.BG_INPUT, fg=theme.FG_PRIMARY, relief="flat",
                         font=theme.FONT_BODY, width=40, bd=8,
                         highlightthickness=1, highlightbackground=theme.BORDER_COLOR,
                         highlightcolor=theme.BG_ACCENT)
        entry.pack(side="left", padx=(4, 0), pady=6)

        # Table
        table_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        table_frame.pack(fill="both", expand=True, padx=30, pady=(4, 20))

        cols = ("roll", "name", "dept", "sem", "phone", "email", "cgpa")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        headers = [("roll", "Roll No", 90), ("name", "Name", 170),
                   ("dept", "Department", 140), ("sem", "Sem", 50),
                   ("phone", "Phone", 110), ("email", "Email", 200),
                   ("cgpa", "CGPA", 70)]
        for cid, text, w in headers:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self.update_selected())

        # Scrollbar
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------
    def refresh_table(self):
        """Reload the treeview with all (or filtered) students."""
        for r in self.tree.get_children():
            self.tree.delete(r)
        search = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        rows = db.fetch_all(
            "SELECT roll_no, name, department, semester, phone, email, cgpa "
            "FROM students ORDER BY roll_no"
        )
        for r in rows:
            line = f"{r['roll_no']} {r['name']} {r.get('department','')}".lower()
            if search and search not in line:
                continue
            self.tree.insert("", "end", values=(
                r["roll_no"], r["name"], r.get("department", ""),
                r.get("semester", ""), r.get("phone", ""), r.get("email", ""),
                r.get("cgpa", 0.0),
            ))

    def _on_select(self, _):
        sel = self.tree.selection()
        if sel:
            self.selected_roll = self.tree.item(sel[0])["values"][0]

    # -------------------------------------------------------------------------
    # Add / Update dialog
    # -------------------------------------------------------------------------
    def open_add_dialog(self, existing=None):
        """Open the add-or-edit student dialog."""
        win = tk.Toplevel(self)
        win.title("Edit Student" if existing else "Add Student")
        win.geometry("460x600")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 460, 600)

        tk.Label(win, text="Edit Student" if existing else "➕ Add New Student",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_SUBTITLE).pack(pady=(20, 16))

        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30, pady=4)

        fields = {}
        labels = [("roll_no", "Roll No"), ("name", "Full Name"),
                  ("department", "Department"), ("semester", "Semester"),
                  ("phone", "Phone"), ("email", "Email"),
                  ("address", "Address"), ("cgpa", "CGPA"),
                  ("dob", "Date of Birth"), ("gender", "Gender")]

        # Department dropdown
        depts = [d["name"] for d in db.fetch_all("SELECT name FROM departments")]
        if not depts:
            depts = ["Computer Science"]

        for i, (key, label) in enumerate(labels):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            if key == "department":
                cb = ttk.Combobox(form, values=depts, width=28, state="readonly")
                cb.current(0)
                cb.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = cb
            elif key == "gender":
                cb = ttk.Combobox(form, values=["Male", "Female", "Other"],
                                  width=28, state="readonly")
                cb.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = cb
            else:
                entry = tk.Entry(form, width=30, bg=theme.BG_INPUT,
                                 fg=theme.FG_PRIMARY, relief="flat", bd=6,
                                 font=theme.FONT_BODY, highlightthickness=1,
                                 highlightbackground=theme.BORDER_COLOR,
                                 highlightcolor=theme.BG_ACCENT)
                entry.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = entry

        # Pre-fill when editing
        if existing:
            for k, w in fields.items():
                if k == "department" or k == "gender":
                    w.set(existing.get(k, ""))
                else:
                    w.insert(0, str(existing.get(k, "") or ""))
            fields["roll_no"].config(state="disabled")

        def save():
            data = {}
            for k, w in fields.items():
                data[k] = w.get().strip()
            # Pre-fill roll number for new students
            if not existing:
                data["roll_no"] = data["roll_no"] or generate_student_id()
            # Validation
            if not data["name"]:
                messagebox.showwarning("Validation", "Name is required.", parent=win)
                return
            if data["email"] and not validate_email(data["email"]):
                messagebox.showwarning("Validation", "Invalid email format.", parent=win)
                return
            try:
                data["semester"] = int(data["semester"]) if data["semester"] else 1
                data["cgpa"] = float(data["cgpa"]) if data["cgpa"] else 0.0
                if not (0 <= data["cgpa"] <= 10):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Validation",
                                       "Semester must be a number and CGPA must be 0-10.",
                                       parent=win)
                return

            if existing:
                db.execute(
                    "UPDATE students SET name=?, department=?, semester=?, phone=?, "
                    "email=?, address=?, cgpa=?, dob=?, gender=? WHERE roll_no=?",
                    (data["name"], data["department"], data["semester"],
                     data["phone"], data["email"], data["address"],
                     data["cgpa"], data["dob"], data["gender"],
                     existing["roll_no"]),
                )
                db.log_activity(f"Updated student {data['name']} ({data['roll_no']})")
                messagebox.showinfo("Success", "Student updated successfully.", parent=win)
            else:
                try:
                    db.execute(
                        "INSERT INTO students (roll_no, name, department, semester, "
                        "phone, email, address, cgpa, dob, gender) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (data["roll_no"], data["name"], data["department"],
                         data["semester"], data["phone"], data["email"],
                         data["address"], data["cgpa"], data["dob"], data["gender"]),
                    )
                    # Auto-create login account for the new student
                    db.execute(
                        "INSERT OR IGNORE INTO users (username, password, role, ref_id) "
                        "VALUES (?,?,?,?)",
                        (data["roll_no"].lower(),
                         __import__("hashlib").sha256("student123".encode()).hexdigest(),
                         "student", data["roll_no"]),
                    )
                    db.log_activity(f"Added student {data['name']} ({data['roll_no']})")
                    messagebox.showinfo("Success",
                                        f"Student added. Default login: "
                                        f"{data['roll_no'].lower()} / student123",
                                        parent=win)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not add student:\n{e}", parent=win)
                    return
            win.destroy()
            self.refresh_table()

        theme.RoundedButton(win, "💾 Save", command=save,
                            width=200, height=44).pack(pady=20)

    def update_selected(self):
        """Edit the currently selected student."""
        if not self.selected_roll:
            messagebox.showwarning("Select", "Please select a student first.")
            return
        row = db.fetch_one("SELECT * FROM students WHERE roll_no = ?",
                           (str(self.selected_roll),))
        if not row:
            messagebox.showerror("Error", "Student not found.")
            return
        self.open_add_dialog(existing=row)

    def delete_selected(self):
        """Delete the selected student after confirmation."""
        if not self.selected_roll:
            messagebox.showwarning("Select", "Please select a student first.")
            return
        if not messagebox.askyesno("Confirm",
                                   f"Delete student {self.selected_roll}?\n"
                                   "This cannot be undone."):
            return
        db.execute("DELETE FROM students WHERE roll_no = ?", (str(self.selected_roll),))
        db.execute("DELETE FROM users WHERE ref_id = ?", (str(self.selected_roll),))
        db.log_activity(f"Deleted student {self.selected_roll}")
        self.selected_roll = None
        self.refresh_table()
        messagebox.showinfo("Deleted", "Student deleted.")

    # -------------------------------------------------------------------------
    # CSV export
    # -------------------------------------------------------------------------
    def export_csv(self):
        """Export all students to a CSV file chosen by the user."""
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"students_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return
        rows = db.fetch_all("SELECT * FROM students ORDER BY roll_no")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else
                                        ["roll_no", "name", "department"])
                writer.writeheader()
                writer.writerows(rows)
            messagebox.showinfo("Export", f"Exported {len(rows)} records to:\n{path}")
            db.log_activity("Exported students to CSV")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}")

    def show_new_id(self):
        """Display the next student ID that would be generated."""
        messagebox.showinfo("New Student ID",
                            f"Next student roll number will be:\n\n"
                            f"  {generate_student_id()}")


# -----------------------------------------------------------------------------
# Student-facing personal profile
# -----------------------------------------------------------------------------
class StudentProfileView(tk.Frame):
    """Personal dashboard for a logged-in student."""

    def __init__(self, parent, roll_no):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.roll_no = roll_no
        self._build_ui()

    def _build_ui(self):
        self.student = db.fetch_one("SELECT * FROM students WHERE roll_no = ?",
                                    (self.roll_no,))
        if not self.student:
            tk.Label(self, text="Student record not found.",
                     bg=theme.BG_PRIMARY, fg=theme.FG_DANGER,
                     font=theme.FONT_BODY).pack(pady=50)
            return

        tk.Label(self, text=f"🎓  {self.student['name']}",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text=f"Roll No: {self.roll_no}  •  "
                            f"{self.student.get('department','')}  •  "
                            f"Semester {self.student.get('semester',1)}",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        # Notebook with tabs
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)

        self._tab_profile(nb)
        self._tab_attendance(nb)
        self._tab_marks(nb)
        self._tab_fees(nb)

    def _tab_profile(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Profile  ")
        info = [
            ("Roll No", self.student.get("roll_no")),
            ("Name", self.student.get("name")),
            ("Department", self.student.get("department")),
            ("Semester", self.student.get("semester")),
            ("Email", self.student.get("email")),
            ("Phone", self.student.get("phone")),
            ("Address", self.student.get("address")),
            ("Date of Birth", self.student.get("dob")),
            ("Gender", self.student.get("gender")),
            ("CGPA", self.student.get("cgpa")),
            ("Admission Date", self.student.get("admission_date")),
        ]
        grid = tk.Frame(tab, bg=theme.BG_PRIMARY)
        grid.pack(padx=40, pady=30)
        for i, (k, v) in enumerate(info):
            tk.Label(grid, text=k, bg=theme.BG_PRIMARY,
                     fg=theme.FG_MUTED, font=theme.FONT_BODY_BOLD,
                     width=16, anchor="w").grid(row=i // 2, column=(i % 2) * 2,
                                                sticky="w", padx=10, pady=8)
            tk.Label(grid, text=str(v or "—"), bg=theme.BG_PRIMARY,
                     fg=theme.FG_PRIMARY, font=theme.FONT_BODY, anchor="w"
                     ).grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w",
                            padx=10, pady=8)

    def _tab_attendance(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Attendance  ")
        rows = db.fetch_all(
            "SELECT subject, date, status FROM attendance "
            "WHERE student_id = ? ORDER BY date DESC", (self.roll_no,)
        )
        present = sum(1 for r in rows if r["status"] == "Present")
        pct = round(present / len(rows) * 100, 1) if rows else 0.0
        tk.Label(tab, text=f"Overall Attendance: {pct}%   "
                           f"({present}/{len(rows)} classes)",
                 bg=theme.BG_PRIMARY, fg=theme.BG_SUCCESS,
                 font=theme.FONT_HEADING).pack(pady=16)

        cols = ("subject", "date", "status")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=14)
        for c, t, w in [("subject", "Subject", 250), ("date", "Date", 180),
                        ("status", "Status", 120)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        for r in rows:
            tree.insert("", "end", values=(r["subject"], r["date"], r["status"]))

    def _tab_marks(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Marks & Grades  ")
        rows = db.fetch_all(
            "SELECT subject, internal, practical, semester_exam, grade "
            "FROM marks WHERE student_id = ?", (self.roll_no,)
        )
        tk.Label(tab, text=f"CGPA: {self.student.get('cgpa', 0.0)} / 10",
                 bg=theme.BG_PRIMARY, fg=theme.BG_ACCENT,
                 font=theme.FONT_HEADING).pack(pady=16)
        cols = ("subject", "internal", "practical", "exam", "grade")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=14)
        for c, t, w in [("subject", "Subject", 220), ("internal", "Internal", 90),
                        ("practical", "Practical", 90), ("exam", "Semester", 90),
                        ("grade", "Grade", 80)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        for r in rows:
            tree.insert("", "end", values=(
                r["subject"], r["internal"], r["practical"],
                r["semester_exam"], r["grade"],
            ))

    def _tab_fees(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Fee Status  ")
        rows = db.fetch_all(
            "SELECT amount, payment_date, status, receipt_no FROM fees "
            "WHERE student_id = ? ORDER BY payment_date DESC", (self.roll_no,)
        )
        paid = sum(r["amount"] for r in rows if r["status"] == "Paid")
        pending = sum(r["amount"] for r in rows if r["status"] != "Paid")
        tk.Label(tab, text=f"Paid: ₹{paid:,.0f}    Pending: ₹{pending:,.0f}",
                 bg=theme.BG_PRIMARY, fg=theme.BG_WARNING,
                 font=theme.FONT_HEADING).pack(pady=16)
        cols = ("amount", "date", "status", "receipt")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        for c, t, w in [("amount", "Amount", 130), ("date", "Date", 160),
                        ("status", "Status", 110), ("receipt", "Receipt", 160)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        for r in rows:
            tree.insert("", "end", values=(
                f"₹{r['amount']:.0f}", r["payment_date"], r["status"],
                r.get("receipt_no", ""),
            ))
