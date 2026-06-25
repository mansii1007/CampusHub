"""
login.py
========
Authentication module for CampusHub.

Provides the LoginWindow class which handles:
    - Admin / Faculty / Student login (role-based)
    - Input validation
    - Password hashing via the Database class
    - "Forgot password" link (admin reset hint)
    - Successful-login callback to launch the main app shell

On a successful authentication it calls `on_success(role, ref_id, username)`
so the caller (main.py) can open the appropriate dashboard.
"""

import tkinter as tk
from tkinter import messagebox

from database import db, hash_password
import theme


class LoginWindow(tk.Tk):
    """Standalone login window that boots the main app on success."""

    def __init__(self, on_success=None):
        super().__init__()
        self.on_success = on_success
        self.title("CampusHub - Login")
        self.geometry("900x560")
        self.resizable(False, False)
        self.configure(bg=theme.BG_PRIMARY)
        theme.center_window(self, 900, 560)

        self._build_ui()

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------
    def _build_ui(self):
        container = tk.Frame(self, bg=theme.BG_PRIMARY)
        container.pack(fill="both", expand=True)

        # --- Left brand panel ---
        brand = tk.Frame(container, bg=theme.BG_SECONDARY, width=400)
        brand.pack(side="left", fill="both")
        brand.pack_propagate(False)

        tk.Label(brand, text="🎓", bg=theme.BG_SECONDARY,
                 fg=theme.FG_PRIMARY, font=("Segoe UI", 64)).pack(pady=(90, 10))
        tk.Label(brand, text="CampusHub", bg=theme.BG_SECONDARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_TITLE).pack()
        tk.Label(brand, text="College Management System",
                 bg=theme.BG_SECONDARY, fg=theme.FG_SECONDARY,
                 font=theme.FONT_BODY).pack(pady=(4, 30))

        features = [
            "• Role-based access (Admin / Faculty / Student)",
            "• Smart attendance & marks management",
            "• Real-time dashboards & reports",
            "• Secure SQLite backend",
        ]
        for f in features:
            tk.Label(brand, text=f, bg=theme.BG_SECONDARY,
                     fg=theme.FG_MUTED, font=theme.FONT_SMALL,
                     anchor="w").pack(fill="x", padx=50, pady=3)

        tk.Label(brand, text="© 2026 CampusHub", bg=theme.BG_SECONDARY,
                 fg=theme.FG_MUTED, font=theme.FONT_SMALL).pack(side="bottom", pady=20)

        # --- Right login form panel ---
        form = tk.Frame(container, bg=theme.BG_PRIMARY)
        form.pack(side="right", fill="both", expand=True)

        inner = tk.Frame(form, bg=theme.BG_PRIMARY)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="Welcome Back 👋", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_TITLE).pack(anchor="w")
        tk.Label(inner, text="Sign in to continue to your dashboard",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", pady=(2, 24))

        # Role selector
        tk.Label(inner, text="Login As", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).pack(anchor="w")
        self.role_var = tk.StringVar(value="admin")
        role_frame = tk.Frame(inner, bg=theme.BG_PRIMARY)
        role_frame.pack(fill="x", pady=(4, 14))
        for role, label in [("admin", "Admin"), ("faculty", "Faculty"),
                            ("student", "Student")]:
            rb = tk.Radiobutton(role_frame, text=label, variable=self.role_var,
                                value=role, bg=theme.BG_PRIMARY,
                                fg=theme.FG_SECONDARY, selectcolor=theme.BG_INPUT,
                                activebackground=theme.BG_PRIMARY,
                                activeforeground=theme.FG_PRIMARY,
                                font=theme.FONT_BODY, bd=0)
            rb.pack(side="left", padx=(0, 18))

        # Username
        tk.Label(inner, text="Username", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).pack(anchor="w")
        self.username_entry = theme.make_entry(inner, placeholder="Enter username")
        self.username_entry.pack(fill="x", pady=(4, 14))

        # Password
        tk.Label(inner, text="Password", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).pack(anchor="w")
        self.password_entry = theme.make_entry(inner, placeholder="Enter password", show="•")
        self.password_entry.pack(fill="x", pady=(4, 8))

        # Forgot password
        fp = tk.Label(inner, text="Forgot password?", bg=theme.BG_PRIMARY,
                      fg=theme.BG_ACCENT, font=theme.FONT_SMALL, cursor="hand2")
        fp.pack(anchor="e")
        fp.bind("<Button-1>", lambda e: self._forgot_password())

        # Login button
        self.login_btn = theme.RoundedButton(
            inner, "Sign In", command=self._attempt_login,
            width=300, height=46
        )
        self.login_btn.pack(pady=(18, 12))

        # Hint
        tk.Label(inner, text="Demo: admin / admin123  •  faculty001 / faculty123  •  student001 / student123",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=("Segoe UI", 8)).pack()

        # Bind Enter key
        self.bind("<Return>", lambda e: self._attempt_login())

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def _attempt_login(self):
        """Validate credentials and dispatch to the on_success callback."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_var.get()

        # ---- Input validation ----
        if not username or username == "Enter username":
            messagebox.showwarning("Validation", "Please enter a username.")
            return
        if not password or password == "Enter password":
            messagebox.showwarning("Validation", "Please enter a password.")
            return

        # ---- Database lookup ----
        hashed = hash_password(password)
        user = db.fetch_one(
            "SELECT * FROM users WHERE username = ? AND password = ? AND role = ?",
            (username, hashed, role),
        )

        if not user:
            messagebox.showerror("Login Failed",
                                 "Invalid username, password, or role.\n"
                                 "Please check your credentials and try again.")
            return

        db.log_activity(f"User '{username}' ({role}) logged in")

        # ---- Success ----
        ref_id = user.get("ref_id", "")
        if self.on_success:
            self.on_success(role, ref_id, username)
        else:
            messagebox.showinfo("Login Success",
                                f"Welcome, {username}! Role: {role}")
        self.destroy()

    def _forgot_password(self):
        """Display recovery instructions (admin-assisted reset)."""
        messagebox.showinfo(
            "Forgot Password",
            "To reset your password, please contact the system administrator:\n\n"
            "📧 admin@campus.edu\n"
            "📞 Campus IT Helpdesk\n\n"
            "For local demo you can reset credentials directly in the "
            "database/campushub.db 'users' table.",
        )


# -----------------------------------------------------------------------------
# Standalone run (for quick testing)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
