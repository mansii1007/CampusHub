"""
admin.py
========
Admin-specific module for CampusHub.

Provides:
    - AdminReportsView : consolidated reports across all modules
                         (Student / Faculty / Attendance / Fee / Result /
                         Course reports) plus CSV export
    - AdminConsole     : utilities (activity log, user management, password
                         reset, backup database)
"""

import os
import csv
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date

from database import db, DB_PATH
import theme


# -----------------------------------------------------------------------------
# Reports view
# -----------------------------------------------------------------------------
class AdminReportsView(tk.Frame):
    """Consolidated reports panel for administrators."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="📈  Reports & Analytics",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Consolidated reports across every module",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        controls = tk.Frame(self, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=30, pady=16)
        tk.Label(controls, text="Report Type:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.report_type = ttk.Combobox(
            controls,
            values=["Student Report", "Faculty Report", "Attendance Report",
                    "Fee Report", "Result Report", "Course Report"],
            state="readonly", width=22)
        self.report_type.set("Student Report")
        self.report_type.pack(side="left", padx=4)
        self.report_type.bind("<<ComboboxSelected>>", lambda e: self.load_report())
        theme.RoundedButton(controls, "🔍 Generate", self.load_report,
                            width=120, height=34).pack(side="left", padx=8)
        theme.RoundedButton(controls, "⤓ Export CSV", self.export_report,
                            width=120, height=34, bg=theme.BG_SUCCESS,
                            hover_bg="#019875").pack(side="left", padx=4)

        table = tk.Frame(self, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self.tree_frame = tk.Frame(table, bg=theme.BG_PRIMARY)
        self.tree_frame.pack(fill="both", expand=True)
        self.load_report()

    def _render_tree(self, columns, rows):
        """Recreate the treeview with the given columns and rows."""
        for w in self.tree_frame.winfo_children():
            w.destroy()
        tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        for c in columns:
            tree.heading(c, text=c.title())
            tree.column(c, width=max(90, 800 // len(columns)), anchor="center")
        tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        for r in rows:
            tree.insert("", "end", values=tuple(r))
        self._last_columns = columns
        self._last_rows = rows

    def load_report(self):
        """Generate the report currently selected in the dropdown."""
        kind = self.report_type.get()
        if kind == "Student Report":
            rows = db.fetch_all("SELECT roll_no, name, department, semester, "
                                "phone, email, cgpa FROM students ORDER BY roll_no")
            self._render_tree(
                ["roll_no", "name", "department", "semester", "phone", "email", "cgpa"],
                [[r.get(c) for c in ["roll_no", "name", "department", "semester",
                                     "phone", "email", "cgpa"]] for r in rows],
            )
        elif kind == "Faculty Report":
            rows = db.fetch_all("SELECT faculty_id, name, department, designation, "
                                "phone, email FROM faculty ORDER BY faculty_id")
            self._render_tree(
                ["faculty_id", "name", "department", "designation", "phone", "email"],
                [[r.get(c) for c in ["faculty_id", "name", "department",
                                     "designation", "phone", "email"]] for r in rows],
            )
        elif kind == "Attendance Report":
            rows = db.fetch_all(
                "SELECT a.student_id, s.name, "
                "SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present, "
                "COUNT(*) AS total FROM attendance a "
                "LEFT JOIN students s ON s.roll_no = a.student_id "
                "GROUP BY a.student_id ORDER BY a.student_id"
            )
            data = []
            for r in rows:
                pct = round(r["present"] / r["total"] * 100, 1) if r["total"] else 0
                data.append([r["student_id"], r.get("name"), r["present"],
                             r["total"], f"{pct}%"])
            self._render_tree(["roll_no", "name", "present", "total", "percent"], data)
        elif kind == "Fee Report":
            rows = db.fetch_all(
                "SELECT student_id, amount, payment_date, status, receipt_no "
                "FROM fees ORDER BY payment_date DESC"
            )
            data = [[r["student_id"], r["amount"], r["payment_date"],
                     r["status"], r.get("receipt_no") or ""] for r in rows]
            self._render_tree(["student_id", "amount", "date", "status", "receipt"], data)
        elif kind == "Result Report":
            rows = db.fetch_all(
                "SELECT s.roll_no, s.name, s.department, s.cgpa FROM students s "
                "ORDER BY s.cgpa DESC"
            )
            data = [[r["roll_no"], r["name"], r["department"], r.get("cgpa") or 0]
                    for r in rows]
            self._render_tree(["roll_no", "name", "department", "cgpa"], data)
        elif kind == "Course Report":
            rows = db.fetch_all("SELECT course_id, course_name, department, "
                                "semester, credits, faculty_id FROM courses ORDER BY course_id")
            data = [[r["course_id"], r["course_name"], r.get("department"),
                     r.get("semester"), r.get("credits"), r.get("faculty_id")] for r in rows]
            self._render_tree(["course_id", "course_name", "department", "semester",
                               "credits", "faculty_id"], data)

    def export_report(self):
        """Export the currently displayed report to CSV."""
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"{self.report_type.get().lower().replace(' ','_')}_"
                        f"{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self._last_columns)
                writer.writerows(self._last_rows)
            messagebox.showinfo("Export",
                                f"Exported {len(self._last_rows)} rows to:\n{path}")
            db.log_activity(f"Exported {self.report_type.get()} report")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}")


# -----------------------------------------------------------------------------
# Admin console
# -----------------------------------------------------------------------------
class AdminConsole(tk.Frame):
    """System utilities: activity log, users, password reset, backup."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="⚙  Admin Console",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="System utilities, user management and backups",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        # Action buttons
        actions = tk.Frame(self, bg=theme.BG_PRIMARY)
        actions.pack(fill="x", padx=30, pady=16)
        theme.RoundedButton(actions, "💾 Backup Database", self.backup_db,
                            width=170, bg=theme.BG_INFO,
                            hover_bg="#3a9fde").pack(side="left", padx=4)
        theme.RoundedButton(actions, "🔑 Reset Password", self.reset_password,
                            width=150, bg=theme.BG_WARNING,
                            hover_bg="#d68910").pack(side="left", padx=4)
        theme.RoundedButton(actions, "➕ Create User", self.create_user,
                            width=130).pack(side="left", padx=4)
        theme.RoundedButton(actions, "👥 View Users", self.view_users,
                            width=120, bg=theme.BG_SUCCESS,
                            hover_bg="#019875").pack(side="left", padx=4)

        # Activity log
        tk.Label(self, text="🕒  Recent Activity Log", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_HEADING).pack(
            anchor="w", padx=30, pady=(6, 8))

        table = tk.Frame(self, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        cols = ("activity", "time")
        self.log_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("activity", "Activity", 520), ("time", "Timestamp", 180)]:
            self.log_tree.heading(c, text=t)
            self.log_tree.column(c, width=w, anchor="w")
        self.log_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._load_log()

    def _load_log(self):
        for r in self.log_tree.get_children():
            self.log_tree.delete(r)
        rows = db.fetch_all("SELECT activity, created_at FROM activity_log "
                            "ORDER BY id DESC LIMIT 100")
        for r in rows:
            self.log_tree.insert("", "end", values=(
                r["activity"], r.get("created_at") or "",
            ))

    # -------------------------------------------------------------------------
    # Backup
    # -------------------------------------------------------------------------
    def backup_db(self):
        """Create a timestamped copy of the SQLite database."""
        folder = filedialog.askdirectory(title="Select destination folder")
        if not folder:
            return
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(folder, f"campushub_backup_{ts}.db")
            shutil.copy2(DB_PATH, dest)
            db.log_activity(f"Database backed up to {dest}")
            messagebox.showinfo("Backup Complete", f"Database saved to:\n{dest}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed:\n{e}")

    # -------------------------------------------------------------------------
    # Password reset
    # -------------------------------------------------------------------------
    def reset_password(self):
        win = tk.Toplevel(self)
        win.title("Reset User Password")
        win.geometry("400x300")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 400, 300)
        tk.Label(win, text="🔑 Reset Password", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack(pady=(18, 14))
        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        usernames = [u["username"] for u in db.fetch_all("SELECT username FROM users")]
        tk.Label(form, text="Username:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).grid(row=0, column=0, pady=8)
        user_cb = ttk.Combobox(form, values=usernames, state="readonly", width=20)
        user_cb.grid(row=0, column=1, pady=8, padx=8)
        tk.Label(form, text="New Password:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).grid(row=1, column=0, pady=8)
        pwd_e = tk.Entry(form, width=22, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                         relief="flat", bd=6, show="•",
                         highlightthickness=1, highlightbackground=theme.BORDER_COLOR,
                         highlightcolor=theme.BG_ACCENT)
        pwd_e.grid(row=1, column=1, pady=8, padx=8)

        def reset():
            u = user_cb.get()
            p = pwd_e.get().strip()
            if not u or not p:
                messagebox.showwarning("Validation", "All fields required.", parent=win)
                return
            from database import hash_password
            db.execute("UPDATE users SET password = ? WHERE username = ?",
                       (hash_password(p), u))
            db.log_activity(f"Admin reset password for user '{u}'")
            messagebox.showinfo("Done", f"Password updated for {u}.", parent=win)
            win.destroy()

        theme.RoundedButton(win, "Reset", command=reset,
                            width=180, height=42).pack(pady=18)

    # -------------------------------------------------------------------------
    # Create user
    # -------------------------------------------------------------------------
    def create_user(self):
        win = tk.Toplevel(self)
        win.title("Create User")
        win.geometry("400x360")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 400, 360)
        tk.Label(win, text="➕ Create User", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack(pady=(18, 14))
        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        fields = {}
        for i, (key, label, kind) in enumerate([
            ("username", "Username", "entry"),
            ("password", "Password", "entry"),
            ("role", "Role", "combo"),
            ("ref_id", "Reference ID", "entry"),
        ]):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY).grid(row=i, column=0, pady=8)
            if kind == "combo":
                cb = ttk.Combobox(form, values=["admin", "faculty", "student"],
                                  state="readonly", width=18)
                cb.set("student")
                cb.grid(row=i, column=1, pady=8, padx=8)
                fields[key] = cb
            else:
                show = "•" if key == "password" else None
                e = tk.Entry(form, width=20, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                             relief="flat", bd=6, show=show,
                             highlightthickness=1, highlightbackground=theme.BORDER_COLOR,
                             highlightcolor=theme.BG_ACCENT)
                e.grid(row=i, column=1, pady=8, padx=8)
                fields[key] = e

        def create():
            data = {k: w.get().strip() for k, w in fields.items()}
            if not all(data.values()):
                messagebox.showwarning("Validation", "All fields required.", parent=win)
                return
            from database import hash_password
            try:
                db.execute(
                    "INSERT INTO users (username, password, role, ref_id) VALUES (?,?,?,?)",
                    (data["username"], hash_password(data["password"]),
                     data["role"], data["ref_id"]),
                )
                db.log_activity(f"Created user '{data['username']}' ({data['role']})")
                messagebox.showinfo("Success", f"User {data['username']} created.", parent=win)
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        theme.RoundedButton(win, "Create", command=create,
                            width=180, height=42).pack(pady=18)

    def view_users(self):
        win = tk.Toplevel(self)
        win.title("User Accounts")
        win.geometry("560x440")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 560, 440)
        tk.Label(win, text="👥  Registered Users", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack(pady=(18, 12))
        table = tk.Frame(win, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        cols = ("username", "role", "ref_id", "created_at")
        tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("username", "Username", 160), ("role", "Role", 110),
                        ("ref_id", "Reference ID", 130), ("created_at", "Created", 170)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        for r in db.fetch_all("SELECT username, role, ref_id, created_at FROM users "
                              "ORDER BY role, username"):
            tree.insert("", "end", values=(r["username"], r["role"],
                                           r.get("ref_id"), r.get("created_at")))
