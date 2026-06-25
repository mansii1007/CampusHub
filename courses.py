"""
courses.py
==========
Course & Department management module for CampusHub.

Provides the CoursesView frame with two tabs:
    - Courses    : create / update / delete courses, assign faculty
    - Departments: create / update / delete departments
"""

import tkinter as tk
from tkinter import ttk, messagebox

from database import db
import theme


class CoursesView(tk.Frame):
    """Admin panel for managing courses and departments."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self.selected_course = None
        self.selected_dept = None
        self._build_ui()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------
    def _build_ui(self):
        tk.Label(self, text="📚  Courses & Departments",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Manage academic courses, credits and departments",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)

        self._tab_courses(nb)
        self._tab_departments(nb)

    # -------------------------------------------------------------------------
    # Courses tab
    # -------------------------------------------------------------------------
    def _tab_courses(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Courses  ")

        actions = tk.Frame(tab, bg=theme.BG_PRIMARY)
        actions.pack(fill="x", padx=10, pady=10)
        theme.RoundedButton(actions, "+ Add Course", self.add_course,
                            width=120).pack(side="left", padx=4)
        theme.RoundedButton(actions, "✎ Update", self.update_course,
                            width=100, bg=theme.BG_INFO,
                            hover_bg="#3a9fde").pack(side="left", padx=4)
        theme.RoundedButton(actions, "🗑 Delete", self.delete_course,
                            width=100, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack(side="left", padx=4)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        cols = ("cid", "name", "dept", "sem", "credits", "faculty")
        self.course_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("cid", "Course ID", 110), ("name", "Course Name", 220),
                        ("dept", "Department", 150), ("sem", "Sem", 60),
                        ("credits", "Credits", 70), ("faculty", "Faculty ID", 120)]:
            self.course_tree.heading(c, text=t)
            self.course_tree.column(c, width=w, anchor="center")
        self.course_tree.pack(fill="both", expand=True, side="left")
        self.course_tree.bind("<<TreeviewSelect>>", self._on_course_select)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.course_tree.yview)
        self.course_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.refresh_courses()

    def refresh_courses(self):
        for r in self.course_tree.get_children():
            self.course_tree.delete(r)
        rows = db.fetch_all("SELECT * FROM courses ORDER BY course_id")
        for r in rows:
            self.course_tree.insert("", "end", values=(
                r["course_id"], r["course_name"], r.get("department"),
                r.get("semester"), r.get("credits"), r.get("faculty_id"),
            ))

    def _on_course_select(self, _):
        sel = self.course_tree.selection()
        if sel:
            self.selected_course = self.course_tree.item(sel[0])["values"][0]

    def _course_dialog(self, existing=None):
        win = tk.Toplevel(self)
        win.title("Course")
        win.geometry("420x460")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 420, 460)
        tk.Label(win, text="Edit Course" if existing else "➕ New Course",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_SUBTITLE).pack(pady=(20, 16))

        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        depts = [d["name"] for d in db.fetch_all("SELECT name FROM departments")] or ["Computer Science"]
        faculty = [f["faculty_id"] for f in db.fetch_all("SELECT faculty_id FROM faculty")]
        if not faculty:
            faculty = ["Unassigned"]

        fields = {}
        items = [("course_id", "Course ID", "entry"),
                 ("course_name", "Course Name", "entry"),
                 ("department", "Department", "combo"),
                 ("semester", "Semester", "entry"),
                 ("credits", "Credits", "entry"),
                 ("faculty_id", "Faculty", "combo")]
        for i, (key, label, kind) in enumerate(items):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            if kind == "combo":
                values = depts if key == "department" else faculty
                cb = ttk.Combobox(form, values=values, width=26, state="readonly")
                cb.set(values[0])
                cb.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = cb
            else:
                e = tk.Entry(form, width=28, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                             relief="flat", bd=6, font=theme.FONT_BODY,
                             highlightthickness=1,
                             highlightbackground=theme.BORDER_COLOR,
                             highlightcolor=theme.BG_ACCENT)
                e.grid(row=i, column=1, pady=6, padx=8)
                fields[key] = e

        if existing:
            for k, w in fields.items():
                if isinstance(w, ttk.Combobox):
                    w.set(existing.get(k, "") or w.get())
                else:
                    w.insert(0, str(existing.get(k, "") or ""))
            fields["course_id"].config(state="disabled")

        def save():
            data = {k: w.get().strip() for k, w in fields.items()}
            if not existing:
                data["course_id"] = data["course_id"] or f"CRS{db.fetch_one('SELECT COUNT(*) AS c FROM courses')['c']+1:03d}"
            if not data["course_name"]:
                messagebox.showwarning("Validation", "Course name required.", parent=win)
                return
            try:
                data["semester"] = int(data["semester"]) if data["semester"] else 1
                data["credits"] = int(data["credits"]) if data["credits"] else 3
            except ValueError:
                messagebox.showwarning("Validation", "Semester and credits must be integers.", parent=win)
                return

            if existing:
                db.execute(
                    "UPDATE courses SET course_name=?, department=?, semester=?, "
                    "credits=?, faculty_id=? WHERE course_id=?",
                    (data["course_name"], data["department"], data["semester"],
                     data["credits"], data["faculty_id"], existing["course_id"]),
                )
                db.log_activity(f"Updated course {data['course_name']}")
            else:
                db.execute(
                    "INSERT INTO courses (course_id, course_name, department, semester, "
                    "credits, faculty_id) VALUES (?,?,?,?,?,?)",
                    (data["course_id"], data["course_name"], data["department"],
                     data["semester"], data["credits"], data["faculty_id"]),
                )
                db.log_activity(f"Created course {data['course_name']}")
            messagebox.showinfo("Success", "Course saved.", parent=win)
            win.destroy()
            self.refresh_courses()

        theme.RoundedButton(win, "💾 Save", command=save, width=200, height=44).pack(pady=20)

    def add_course(self):
        self._course_dialog()

    def update_course(self):
        if not self.selected_course:
            messagebox.showwarning("Select", "Please select a course.")
            return
        row = db.fetch_one("SELECT * FROM courses WHERE course_id = ?",
                           (str(self.selected_course),))
        if row:
            self._course_dialog(existing=row)

    def delete_course(self):
        if not self.selected_course:
            messagebox.showwarning("Select", "Please select a course.")
            return
        if messagebox.askyesno("Confirm", f"Delete course {self.selected_course}?"):
            db.execute("DELETE FROM courses WHERE course_id = ?", (str(self.selected_course),))
            db.log_activity(f"Deleted course {self.selected_course}")
            self.selected_course = None
            self.refresh_courses()

    # -------------------------------------------------------------------------
    # Departments tab
    # -------------------------------------------------------------------------
    def _tab_departments(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Departments  ")

        actions = tk.Frame(tab, bg=theme.BG_PRIMARY)
        actions.pack(fill="x", padx=10, pady=10)
        theme.RoundedButton(actions, "+ Add Dept", self.add_dept,
                            width=120).pack(side="left", padx=4)
        theme.RoundedButton(actions, "🗑 Delete", self.delete_dept,
                            width=110, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack(side="left", padx=4)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        cols = ("name", "hod", "desc", "students")
        self.dept_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("name", "Department", 180), ("hod", "HOD", 180),
                        ("desc", "Description", 240), ("students", "Students", 90)]:
            self.dept_tree.heading(c, text=t)
            self.dept_tree.column(c, width=w, anchor="center")
        self.dept_tree.pack(fill="both", expand=True, side="left")
        self.dept_tree.bind("<<TreeviewSelect>>", self._on_dept_select)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.dept_tree.yview)
        self.dept_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.refresh_depts()

    def refresh_depts(self):
        for r in self.dept_tree.get_children():
            self.dept_tree.delete(r)
        rows = db.fetch_all("SELECT * FROM departments ORDER BY name")
        for r in rows:
            count = db.fetch_one(
                "SELECT COUNT(*) AS c FROM students WHERE department = ?",
                (r["name"],)
            )
            self.dept_tree.insert("", "end", values=(
                r["name"], r.get("hod"), r.get("description"),
                count["c"] if count else 0,
            ))

    def _on_dept_select(self, _):
        sel = self.dept_tree.selection()
        if sel:
            self.selected_dept = self.dept_tree.item(sel[0])["values"][0]

    def add_dept(self):
        win = tk.Toplevel(self)
        win.title("Add Department")
        win.geometry("400x340")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 400, 340)
        tk.Label(win, text="➕ New Department", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack(pady=(20, 16))
        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        fields = {}
        for i, (key, label) in enumerate([("name", "Department Name"),
                                          ("hod", "Head of Dept"),
                                          ("description", "Description")]):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            e = tk.Entry(form, width=26, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                         relief="flat", bd=6, font=theme.FONT_BODY,
                         highlightthickness=1,
                         highlightbackground=theme.BORDER_COLOR,
                         highlightcolor=theme.BG_ACCENT)
            e.grid(row=i, column=1, pady=6, padx=8)
            fields[key] = e

        def save():
            data = {k: w.get().strip() for k, w in fields.items()}
            if not data["name"]:
                messagebox.showwarning("Validation", "Department name required.", parent=win)
                return
            try:
                db.execute("INSERT OR IGNORE INTO departments (name, hod, description) VALUES (?,?,?)",
                           (data["name"], data["hod"], data["description"]))
                db.log_activity(f"Added department {data['name']}")
                messagebox.showinfo("Success", "Department added.", parent=win)
                win.destroy()
                self.refresh_depts()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        theme.RoundedButton(win, "💾 Save", command=save, width=200, height=44).pack(pady=20)

    def delete_dept(self):
        if not self.selected_dept:
            messagebox.showwarning("Select", "Please select a department.")
            return
        if messagebox.askyesno("Confirm", f"Delete department '{self.selected_dept}'?"):
            db.execute("DELETE FROM departments WHERE name = ?", (str(self.selected_dept),))
            db.log_activity(f"Deleted department {self.selected_dept}")
            self.selected_dept = None
            self.refresh_depts()
