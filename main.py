"""
main.py
=======
Entry point for CampusHub - College Management System.

Run with:
    python main.py

Flow:
    1. Initialise the database (schema + seed data).
    2. Show the LoginWindow.
    3. On successful authentication, launch the role-specific app shell
       (AdminShell / FacultyShell / StudentShell), each of which provides
       a sidebar navigation and content area.
"""

import tkinter as tk
from tkinter import messagebox

import theme
from database import db
from login import LoginWindow
from dashboard import DashboardView
from students import StudentsView, StudentProfileView
from faculty import FacultyView, FacultyProfileView
from courses import CoursesView
from attendance import AttendanceView
from marks import MarksView
from fees import FeesView
from library import LibraryView
from timetable import TimetableView
from admin import AdminReportsView, AdminConsole


# -----------------------------------------------------------------------------
# Base application shell with sidebar navigation
# -----------------------------------------------------------------------------
class AppShell(tk.Tk):
    """
    Common base for the role-specific shells.

    Provides:
        - A fixed sidebar with navigation buttons
        - A scrollable content area that swaps views
        - A top bar with role/user info and a logout button
    """

    def __init__(self, role, ref_id, username):
        super().__init__()
        self.role = role
        self.ref_id = ref_id
        self.username = username
        self.title(f"CampusHub - {role.capitalize()} Dashboard")
        self.geometry(theme.DEFAULT_GEOMETRY)
        self.minsize(1100, 680)
        theme.apply_theme(self)

        self._build_skeleton()
        self.show_first_view()

    # -------------------------------------------------------------------------
    # Skeleton
    # -------------------------------------------------------------------------
    def _build_skeleton(self):
        # Sidebar
        self.sidebar = tk.Frame(self, bg=theme.BG_SECONDARY, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand
        brand = tk.Frame(self.sidebar, bg=theme.BG_SECONDARY)
        brand.pack(fill="x", pady=(18, 10), padx=16)
        tk.Label(brand, text="🎓", bg=theme.BG_SECONDARY,
                 fg=theme.FG_PRIMARY, font=("Segoe UI", 26)).pack()
        tk.Label(brand, text="CampusHub", bg=theme.BG_SECONDARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack()
        tk.Label(brand, text=self.role.capitalize(),
                 bg=theme.BG_SECONDARY, fg=theme.BG_ACCENT,
                 font=theme.FONT_SMALL).pack()

        # Nav container
        self.nav = tk.Frame(self.sidebar, bg=theme.BG_SECONDARY)
        self.nav.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Footer of sidebar - logout
        footer = tk.Frame(self.sidebar, bg=theme.BG_SECONDARY)
        footer.pack(fill="x", padx=12, pady=(0, 14))
        theme.RoundedButton(footer, "⎋ Logout", command=self.logout,
                            width=200, height=38, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack()

        # Main area
        main = tk.Frame(self, bg=theme.BG_PRIMARY)
        main.pack(side="right", fill="both", expand=True)

        # Top bar
        self.topbar = tk.Frame(main, bg=theme.BG_SECONDARY, height=52)
        self.topbar.pack(side="top", fill="x")
        self.topbar.pack_propagate(False)
        self.top_title = tk.Label(self.topbar, text="Dashboard",
                                  bg=theme.BG_SECONDARY, fg=theme.FG_PRIMARY,
                                  font=theme.FONT_HEADING)
        self.top_title.pack(side="left", padx=22)
        tk.Label(self.topbar, text=f"👤 {self.username}",
                 bg=theme.BG_SECONDARY, fg=theme.FG_SECONDARY,
                 font=theme.FONT_BODY).pack(side="right", padx=22)

        # Content
        self.content = tk.Frame(main, bg=theme.BG_PRIMARY)
        self.content.pack(fill="both", expand=True)
        self.current_view = None

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------
    def build_nav(self, items):
        """
        Build sidebar buttons from a list of (label, callback) tuples.
        """
        for child in self.nav.winfo_children():
            child.destroy()
        for label, callback in items:
            btn = tk.Button(self.nav, text=label, command=callback,
                            bg=theme.BG_SECONDARY, fg=theme.FG_SECONDARY,
                            activebackground=theme.BG_ACCENT,
                            activeforeground=theme.FG_PRIMARY,
                            font=theme.FONT_BODY, bd=0, anchor="w",
                            padx=16, pady=10, cursor="hand2",
                            relief="flat", overrelief="flat",
                            highlightthickness=0)
            btn.pack(fill="x", pady=2)
            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=theme.BG_ACCENT,
                                                          fg=theme.FG_PRIMARY))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=theme.BG_SECONDARY,
                                                          fg=theme.FG_SECONDARY))

    def switch_view(self, title, view_class, *args, **kwargs):
        """Destroy the current view and instantiate a new one in content."""
        if self.current_view is not None:
            self.current_view.destroy()
        self.top_title.config(text=title)
        self.current_view = view_class(self.content, *args, **kwargs)
        self.current_view.pack(fill="both", expand=True)

    def show_first_view(self):
        """Implemented by subclasses to set their default view + nav."""
        raise NotImplementedError

    def logout(self):
        """Close the shell and relaunch the login window."""
        if messagebox.askyesno("Logout", "Log out of CampusHub?"):
            db.log_activity(f"User '{self.username}' logged out")
            self.destroy()
            # Relaunch login
            login = LoginWindow(on_success=launch_app)
            login.mainloop()


# -----------------------------------------------------------------------------
# Admin shell
# -----------------------------------------------------------------------------
class AdminShell(AppShell):
    """Full-featured shell shown to administrators."""

    def show_first_view(self):
        nav = [
            ("📊  Dashboard", lambda: self.switch_view("Dashboard", DashboardView,
                                                      role=self.role, ref_id=self.ref_id,
                                                      username=self.username)),
            ("👥  Students", lambda: self.switch_view("Students", StudentsView,
                                                      role=self.role)),
            ("👩‍🏫  Faculty", lambda: self.switch_view("Faculty", FacultyView,
                                                       role=self.role)),
            ("📚  Courses & Depts", lambda: self.switch_view("Courses & Departments",
                                                             CoursesView, role=self.role)),
            ("📅  Attendance", lambda: self.switch_view("Attendance", AttendanceView,
                                                        role=self.role)),
            ("📊  Marks & Grades", lambda: self.switch_view("Marks & Grades",
                                                            MarksView, role=self.role)),
            ("💰  Fees", lambda: self.switch_view("Fees", FeesView, role=self.role)),
            ("📖  Library", lambda: self.switch_view("Library", LibraryView,
                                                     role=self.role)),
            ("🗓  Timetable", lambda: self.switch_view("Timetable", TimetableView,
                                                       role=self.role)),
            ("📈  Reports", lambda: self.switch_view("Reports", AdminReportsView,
                                                     role=self.role)),
            ("⚙  Admin Console", lambda: self.switch_view("Admin Console",
                                                           AdminConsole, role=self.role)),
        ]
        self.build_nav(nav)
        # Default to dashboard
        nav[0][1]()


# -----------------------------------------------------------------------------
# Faculty shell
# -----------------------------------------------------------------------------
class FacultyShell(AppShell):
    """Shell shown to faculty members."""

    def show_first_view(self):
        faculty = db.fetch_one("SELECT * FROM faculty WHERE faculty_id = ?",
                               (self.ref_id,))
        dept = faculty.get("department") if faculty else None
        nav = [
            ("📊  Dashboard", lambda: self.switch_view("Dashboard", DashboardView,
                                                      role=self.role, ref_id=self.ref_id,
                                                      username=self.username)),
            ("👩‍🏫  My Profile", lambda: self.switch_view("My Profile",
                                                          FacultyProfileView, self.ref_id)),
            ("📅  Attendance", lambda: self.switch_view("Attendance", AttendanceView,
                                                        role=self.role, faculty_dept=dept)),
            ("📊  Upload Marks", lambda: self.switch_view("Marks", MarksView, role=self.role)),
            ("👥  Student List", lambda: self.switch_view("My Students",
                                                          FacultyProfileView, self.ref_id)),
            ("🗓  Timetable", lambda: self.switch_view("Timetable", TimetableView,
                                                       role=self.role)),
        ]
        self.build_nav(nav)
        nav[0][1]()


# -----------------------------------------------------------------------------
# Student shell
# -----------------------------------------------------------------------------
class StudentShell(AppShell):
    """Shell shown to students."""

    def show_first_view(self):
        nav = [
            ("📊  Dashboard", lambda: self.switch_view("Dashboard", DashboardView,
                                                      role=self.role, ref_id=self.ref_id,
                                                      username=self.username)),
            ("🎓  My Profile", lambda: self.switch_view("My Profile",
                                                        StudentProfileView, self.ref_id)),
            ("🗓  Timetable", lambda: self.switch_view("Timetable", TimetableView,
                                                       role=self.role)),
            ("📖  Library", lambda: self.switch_view("Library", LibraryView, role=self.role)),
        ]
        self.build_nav(nav)
        nav[0][1]()


# -----------------------------------------------------------------------------
# Launcher
# -----------------------------------------------------------------------------
def launch_app(role: str, ref_id: str, username: str):
    """Factory function called by LoginWindow on a successful login."""
    if role == "admin":
        AdminShell(role, ref_id, username).mainloop()
    elif role == "faculty":
        FacultyShell(role, ref_id, username).mainloop()
    elif role == "student":
        StudentShell(role, ref_id, username).mainloop()


# -----------------------------------------------------------------------------
# Main entry
# -----------------------------------------------------------------------------
def main():
    """Boot the database and present the login window."""
    # Database is initialised on import, but we touch `db` here to be explicit
    # and to surface any connection errors early.
    try:
        db.log_activity("Application started")
    except Exception as e:
        print(f"[FATAL] Could not initialise database: {e}")
        return

    login = LoginWindow(on_success=launch_app)
    login.mainloop()


if __name__ == "__main__":
    main()
