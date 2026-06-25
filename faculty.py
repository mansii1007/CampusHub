"""
faculty.py
==========
Faculty management module for CampusHub.

Provides:
    - FacultyView      : Admin CRUD for faculty members
    - FacultyProfileView : Faculty-facing dashboard (assigned subjects,
                           attendance entry, marks upload, student lists)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from database import db
import theme


def generate_faculty_id() -> str:
    """Generate the next faculty ID, e.g. FAC001."""
    row = db.fetch_one("SELECT COUNT(*) AS c FROM faculty")
    count = row["c"] if row else 0
    return f"FAC{count + 1:03d}"


class FacultyView(tk.Frame):
    """Admin panel for managing faculty members."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self.selected_id = None
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        tk.Label(self, text="👩‍🏫  Faculty Management",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Add faculty, assign subjects, manage records",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        actions = tk.Frame(self, bg=theme.BG_PRIMARY)
        actions.pack(fill="x", padx=30, pady=14)
        theme.RoundedButton(actions, "+ Add Faculty", self.open_add_dialog,
                            width=130).pack(side="left", padx=(0, 8))
        theme.RoundedButton(actions, "✎ Update", self.update_selected,
                            width=110, bg=theme.BG_INFO,
                            hover_bg="#3a9fde").pack(side="left", padx=4)
        theme.RoundedButton(actions, "🗑 Delete", self.delete_selected,
                            width=110, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack(side="left", padx=4)
        theme.RoundedButton(actions, "🆔 New ID", self.show_new_id,
                            width=100, bg=theme.BG_WARNING,
                            hover_bg="#d68910").pack(side="left", padx=4)

        # Table
        table_frame = tk.Frame(self, bg=theme.BG_PRIMARY)
        table_frame.pack(fill="both", expand=True, padx=30, pady=(4, 20))
        cols = ("fid", "name", "dept", "desig", "phone", "email", "subjects")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        headers = [("fid", "Faculty ID", 90), ("name", "Name", 160),
                   ("dept", "Department", 140), ("desig", "Designation", 120),
                   ("phone", "Phone", 110), ("email", "Email", 200),
                   ("subjects", "Subjects", 180)]
        for cid, text, w in headers:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self.update_selected())
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def refresh_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        rows = db.fetch_all("SELECT * FROM faculty ORDER BY faculty_id")
        for r in rows:
            self.tree.insert("", "end", values=(
                r["faculty_id"], r["name"], r.get("department", ""),
                r.get("designation", ""), r.get("phone", ""),
                r.get("email", ""), r.get("subjects", ""),
            ))

    def _on_select(self, _):
        sel = self.tree.selection()
        if sel:
            self.selected_id = self.tree.item(sel[0])["values"][0]

    def open_add_dialog(self, existing=None):
        win = tk.Toplevel(self)
        win.title("Edit Faculty" if existing else "Add Faculty")
        win.geometry("460x540")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 460, 540)

        tk.Label(win, text="Edit Faculty" if existing else "➕ Add Faculty Member",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_SUBTITLE).pack(pady=(20, 16))

        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        depts = [d["name"] for d in db.fetch_all("SELECT name FROM departments")] or ["Computer Science"]
        desigs = ["Professor", "Associate Professor", "Assistant Professor", "Lecturer"]

        fields = {}
        for i, (key, label, kind) in enumerate([
            ("faculty_id", "Faculty ID", "entry"),
            ("name", "Full Name", "entry"),
            ("department", "Department", "combo"),
            ("designation", "Designation", "combo"),
            ("phone", "Phone", "entry"),
            ("email", "Email", "entry"),
            ("subjects", "Subjects (comma separated)", "entry"),
        ]):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            if kind == "combo":
                values = depts if key == "department" else desigs
                cb = ttk.Combobox(form, values=values, width=28, state="readonly")
                cb.current(0)
                cb.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = cb
            else:
                e = tk.Entry(form, width=30, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                             relief="flat", bd=6, font=theme.FONT_BODY,
                             highlightthickness=1,
                             highlightbackground=theme.BORDER_COLOR,
                             highlightcolor=theme.BG_ACCENT)
                e.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = e

        if existing:
            for k, w in fields.items():
                if isinstance(w, ttk.Combobox):
                    w.set(existing.get(k, ""))
                else:
                    w.insert(0, str(existing.get(k, "") or ""))
            fields["faculty_id"].config(state="disabled")

        def save():
            data = {k: w.get().strip() for k, w in fields.items()}
            if not existing:
                data["faculty_id"] = data["faculty_id"] or generate_faculty_id()
            if not data["name"]:
                messagebox.showwarning("Validation", "Name is required.", parent=win)
                return
            if existing:
                db.execute(
                    "UPDATE faculty SET name=?, department=?, designation=?, "
                    "phone=?, email=?, subjects=? WHERE faculty_id=?",
                    (data["name"], data["department"], data["designation"],
                     data["phone"], data["email"], data["subjects"],
                     existing["faculty_id"]),
                )
                db.log_activity(f"Updated faculty {data['name']} ({data['faculty_id']})")
                messagebox.showinfo("Success", "Faculty updated.", parent=win)
            else:
                try:
                    db.execute(
                        "INSERT INTO faculty (faculty_id, name, department, "
                        "designation, phone, email, subjects) VALUES (?,?,?,?,?,?,?)",
                        (data["faculty_id"], data["name"], data["department"],
                         data["designation"], data["phone"], data["email"],
                         data["subjects"]),
                    )
                    db.execute(
                        "INSERT OR IGNORE INTO users (username, password, role, ref_id) "
                        "VALUES (?,?,?,?)",
                        (data["faculty_id"].lower(),
                         __import__("hashlib").sha256("faculty123".encode()).hexdigest(),
                         "faculty", data["faculty_id"]),
                    )
                    db.log_activity(f"Added faculty {data['name']} ({data['faculty_id']})")
                    messagebox.showinfo("Success",
                                        f"Faculty added. Login: "
                                        f"{data['faculty_id'].lower()} / faculty123",
                                        parent=win)
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=win)
                    return
            win.destroy()
            self.refresh_table()

        theme.RoundedButton(win, "💾 Save", command=save,
                            width=200, height=44).pack(pady=20)

    def update_selected(self):
        if not self.selected_id:
            messagebox.showwarning("Select", "Please select a faculty member.")
            return
        row = db.fetch_one("SELECT * FROM faculty WHERE faculty_id = ?",
                           (str(self.selected_id),))
        if row:
            self.open_add_dialog(existing=row)

    def delete_selected(self):
        if not self.selected_id:
            messagebox.showwarning("Select", "Please select a faculty member.")
            return
        if not messagebox.askyesno("Confirm",
                                   f"Delete faculty {self.selected_id}?"):
            return
        db.execute("DELETE FROM faculty WHERE faculty_id = ?", (str(self.selected_id),))
        db.execute("DELETE FROM users WHERE ref_id = ?", (str(self.selected_id),))
        db.log_activity(f"Deleted faculty {self.selected_id}")
        self.selected_id = None
        self.refresh_table()

    def show_new_id(self):
        messagebox.showinfo("New Faculty ID",
                            f"Next faculty ID will be: {generate_faculty_id()}")


# -----------------------------------------------------------------------------
# Faculty-facing workspace
# -----------------------------------------------------------------------------
class FacultyProfileView(tk.Frame):
    """Workspace shown when a faculty member logs in."""

    def __init__(self, parent, faculty_id):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.faculty_id = faculty_id
        self.faculty = db.fetch_one("SELECT * FROM faculty WHERE faculty_id = ?",
                                    (faculty_id,))
        self._build_ui()

    def _build_ui(self):
        if not self.faculty:
            tk.Label(self, text="Faculty record not found.",
                     bg=theme.BG_PRIMARY, fg=theme.FG_DANGER,
                     font=theme.FONT_BODY).pack(pady=50)
            return

        tk.Label(self, text=f"👩‍🏫  {self.faculty['name']}",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text=f"{self.faculty_id}  •  "
                            f"{self.faculty.get('designation','')}  •  "
                            f"{self.faculty.get('department','')}",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)
        self._tab_profile(nb)
        self._tab_students(nb)

    def _tab_profile(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Profile & Subjects  ")
        info = [("Faculty ID", self.faculty.get("faculty_id")),
                ("Name", self.faculty.get("name")),
                ("Department", self.faculty.get("department")),
                ("Designation", self.faculty.get("designation")),
                ("Email", self.faculty.get("email")),
                ("Phone", self.faculty.get("phone")),
                ("Assigned Subjects", self.faculty.get("subjects"))]
        grid = tk.Frame(tab, bg=theme.BG_PRIMARY)
        grid.pack(padx=40, pady=30)
        for i, (k, v) in enumerate(info):
            tk.Label(grid, text=k, bg=theme.BG_PRIMARY,
                     fg=theme.FG_MUTED, font=theme.FONT_BODY_BOLD,
                     anchor="w", width=18).grid(row=i, column=0, sticky="w", pady=8)
            tk.Label(grid, text=str(v or "—"), bg=theme.BG_PRIMARY,
                     fg=theme.FG_PRIMARY, font=theme.FONT_BODY, anchor="w"
                     ).grid(row=i, column=1, sticky="w", pady=8, padx=10)

    def _tab_students(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Student List  ")
        dept = self.faculty.get("department")
        rows = db.fetch_all(
            "SELECT roll_no, name, semester, phone, email FROM students "
            "WHERE department = ? ORDER BY roll_no", (dept,)
        )
        tk.Label(tab, text=f"Students in {dept} department",
                 bg=theme.BG_PRIMARY, fg=theme.FG_SECONDARY,
                 font=theme.FONT_HEADING).pack(pady=16)
        cols = ("roll", "name", "sem", "phone", "email")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=14)
        for c, t, w in [("roll", "Roll No", 110), ("name", "Name", 180),
                        ("sem", "Sem", 70), ("phone", "Phone", 130),
                        ("email", "Email", 220)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        for r in rows:
            tree.insert("", "end", values=(
                r["roll_no"], r["name"], r.get("semester"),
                r.get("phone"), r.get("email"),
            ))
        if not rows:
            tree.insert("", "end", values=("—", "No students found", "", "", ""))
