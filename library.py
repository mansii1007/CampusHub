"""
library.py
==========
Library management module for CampusHub.

Provides the LibraryView frame with:
    - Book database (add / update / delete)
    - Issue book (auto-mark unavailable, set due date)
    - Return book (auto-calculate fine: ₹5/day beyond 14-day window)
    - Available books view
    - Issued books view
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta

from database import db
import theme


# Fine policy
FINE_PER_DAY = 5            # ₹5 per day overdue
LOAN_PERIOD_DAYS = 14       # default loan window


def compute_fine(issue_date_str: str) -> float:
    """Calculate fine based on issue date and the loan period."""
    try:
        issue_d = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0.0
    due = issue_d + timedelta(days=LOAN_PERIOD_DAYS)
    overdue = (date.today() - due).days
    return max(0, overdue) * FINE_PER_DAY


class LibraryView(tk.Frame):
    """Admin / librarian panel for book management."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self.selected_book = None
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="📖  Library Management",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Manage books, issue/return and calculate fines",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)
        self._tab_books(nb)
        self._tab_issue(nb)
        self._tab_available(nb)
        self._tab_issued(nb)

    # -------------------------------------------------------------------------
    # Books database tab
    # -------------------------------------------------------------------------
    def _tab_books(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Book Database  ")

        actions = tk.Frame(tab, bg=theme.BG_PRIMARY)
        actions.pack(fill="x", padx=12, pady=10)
        theme.RoundedButton(actions, "+ Add Book", self.add_book,
                            width=110).pack(side="left", padx=4)
        theme.RoundedButton(actions, "🗑 Delete", self.delete_book,
                            width=100, bg=theme.BG_DANGER,
                            hover_bg="#d83b2c").pack(side="left", padx=4)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        cols = ("bid", "name", "author", "category", "availability")
        self.book_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("bid", "Book ID", 100), ("name", "Book Name", 240),
                        ("author", "Author", 180), ("category", "Category", 140),
                        ("availability", "Status", 120)]:
            self.book_tree.heading(c, text=t)
            self.book_tree.column(c, width=w, anchor="center")
        self.book_tree.pack(fill="both", expand=True, side="left")
        self.book_tree.bind("<<TreeviewSelect>>", self._on_book_select)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.book_tree.yview)
        self.book_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.refresh_books()

    def refresh_books(self):
        for r in self.book_tree.get_children():
            self.book_tree.delete(r)
        rows = db.fetch_all("SELECT * FROM library ORDER BY book_id")
        for r in rows:
            self.book_tree.insert("", "end", values=(
                r["book_id"], r["book_name"], r.get("author"),
                r.get("category"), r.get("availability"),
            ))

    def _on_book_select(self, _):
        sel = self.book_tree.selection()
        if sel:
            self.selected_book = self.book_tree.item(sel[0])["values"][0]

    def add_book(self):
        win = tk.Toplevel(self)
        win.title("Add Book")
        win.geometry("400x380")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 400, 380)
        tk.Label(win, text="➕ Add New Book", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_SUBTITLE).pack(pady=(18, 14))

        form = tk.Frame(win, bg=theme.BG_PRIMARY)
        form.pack(padx=30)
        fields = {}
        for i, (key, label) in enumerate([("book_id", "Book ID"),
                                          ("book_name", "Book Name"),
                                          ("author", "Author"),
                                          ("category", "Category")]):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            e = tk.Entry(form, width=24, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                         relief="flat", bd=6, font=theme.FONT_BODY,
                         highlightthickness=1, highlightbackground=theme.BORDER_COLOR,
                         highlightcolor=theme.BG_ACCENT)
            e.grid(row=i, column=1, pady=6, padx=8)
            fields[key] = e
        # Pre-fill next book id
        count = db.fetch_one("SELECT COUNT(*) AS c FROM library")["c"] + 1
        fields["book_id"].insert(0, f"BK{count:04d}")

        def save():
            data = {k: w.get().strip() for k, w in fields.items()}
            if not data["book_name"]:
                messagebox.showwarning("Validation", "Book name required.", parent=win)
                return
            try:
                db.execute(
                    "INSERT INTO library (book_id, book_name, author, category, "
                    "availability) VALUES (?,?,?,?,?)",
                    (data["book_id"], data["book_name"], data["author"],
                     data["category"], "Available"),
                )
                db.log_activity(f"Added book '{data['book_name']}'")
                messagebox.showinfo("Success", "Book added.", parent=win)
                win.destroy()
                self.refresh_books()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        theme.RoundedButton(win, "💾 Save", command=save, width=180, height=42).pack(pady=18)

    def delete_book(self):
        if not self.selected_book:
            messagebox.showwarning("Select", "Please select a book.")
            return
        if messagebox.askyesno("Confirm", f"Delete book {self.selected_book}?"):
            db.execute("DELETE FROM library WHERE book_id = ?", (str(self.selected_book),))
            db.log_activity(f"Deleted book {self.selected_book}")
            self.selected_book = None
            self.refresh_books()

    # -------------------------------------------------------------------------
    # Issue / return tab
    # -------------------------------------------------------------------------
    def _tab_issue(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Issue / Return  ")

        # Issue section
        issue_frm = tk.Frame(tab, bg=theme.BG_PRIMARY)
        issue_frm.pack(fill="x", padx=20, pady=16)
        tk.Label(issue_frm, text="📥 Issue Book", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_HEADING).pack(anchor="w")

        row = tk.Frame(issue_frm, bg=theme.BG_PRIMARY)
        row.pack(fill="x", pady=6)
        tk.Label(row, text="Book:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        avail_books = [b["book_id"] for b in db.fetch_all(
            "SELECT book_id FROM library WHERE availability='Available'")]
        self.issue_book = ttk.Combobox(row, values=avail_books, width=18, state="readonly")
        self.issue_book.pack(side="left", padx=4)
        tk.Label(row, text="Student Roll:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        self.issue_stu = tk.Entry(row, width=14, bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                                  relief="flat", bd=5, highlightthickness=1,
                                  highlightbackground=theme.BORDER_COLOR,
                                  highlightcolor=theme.BG_ACCENT)
        self.issue_stu.pack(side="left", padx=4)
        theme.RoundedButton(row, "Issue", self.issue_book_action,
                            width=80, height=32, bg=theme.BG_INFO,
                            hover_bg="#3a9fde").pack(side="left", padx=8)

        # Return section
        ret_frm = tk.Frame(tab, bg=theme.BG_PRIMARY)
        ret_frm.pack(fill="x", padx=20, pady=6)
        tk.Label(ret_frm, text="📤 Return Book", bg=theme.BG_PRIMARY,
                 fg=theme.FG_PRIMARY, font=theme.FONT_HEADING).pack(anchor="w")

        row2 = tk.Frame(ret_frm, bg=theme.BG_PRIMARY)
        row2.pack(fill="x", pady=6)
        tk.Label(row2, text="Book ID:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        issued_books = [b["book_id"] for b in db.fetch_all(
            "SELECT book_id FROM library WHERE availability='Issued'")]
        self.ret_book = ttk.Combobox(row2, values=issued_books, width=18, state="readonly")
        self.ret_book.pack(side="left", padx=4)
        theme.RoundedButton(row2, "Return", self.return_book_action,
                            width=90, height=32, bg=theme.BG_SUCCESS,
                            hover_bg="#019875").pack(side="left", padx=8)

        self.fine_lbl = tk.Label(tab, text="", bg=theme.BG_PRIMARY,
                                 fg=theme.BG_WARNING, font=theme.FONT_HEADING)
        self.fine_lbl.pack(pady=10)

    def issue_book_action(self):
        book_id = self.issue_book.get()
        roll = self.issue_stu.get().strip()
        if not book_id or not roll:
            messagebox.showwarning("Validation", "Select book and enter roll number.")
            return
        student = db.fetch_one("SELECT roll_no FROM students WHERE roll_no = ?", (roll,))
        if not student:
            messagebox.showerror("Error", f"Student {roll} not found.")
            return
        today = date.today().isoformat()
        due = (date.today() + timedelta(days=LOAN_PERIOD_DAYS)).isoformat()
        db.execute(
            "UPDATE library SET availability='Issued', issued_to=?, issue_date=?, "
            "return_date=?, fine=0 WHERE book_id=?",
            (roll, today, due, book_id),
        )
        db.log_activity(f"Issued book {book_id} to {roll}")
        messagebox.showinfo("Issued",
                            f"Book {book_id} issued to {roll}.\nDue date: {due}")
        self._refresh_combos()

    def return_book_action(self):
        book_id = self.ret_book.get()
        if not book_id:
            messagebox.showwarning("Validation", "Select a book to return.")
            return
        book = db.fetch_one("SELECT * FROM library WHERE book_id = ?", (book_id,))
        if not book:
            return
        fine = compute_fine(book.get("issue_date"))
        db.execute(
            "UPDATE library SET availability='Available', issued_to=NULL, "
            "issue_date=NULL, return_date=NULL, fine=? WHERE book_id=?",
            (fine, book_id),
        )
        db.log_activity(f"Returned book {book_id} (fine ₹{fine})")
        if fine > 0:
            self.fine_lbl.config(text=f"⚠ Overdue fine for {book_id}: ₹{fine}")
        else:
            self.fine_lbl.config(text=f"✓ Book {book_id} returned. No fine.", fg=theme.BG_SUCCESS)
        messagebox.showinfo("Returned",
                            f"Book {book_id} returned.\nFine: ₹{fine}")
        self._refresh_combos()

    def _refresh_combos(self):
        self.issue_book["values"] = [b["book_id"] for b in db.fetch_all(
            "SELECT book_id FROM library WHERE availability='Available'")]
        self.ret_book["values"] = [b["book_id"] for b in db.fetch_all(
            "SELECT book_id FROM library WHERE availability='Issued'")]

    # -------------------------------------------------------------------------
    # Available / Issued tabs
    # -------------------------------------------------------------------------
    def _tab_available(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Available Books  ")
        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=12)
        cols = ("bid", "name", "author", "category")
        tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("bid", "Book ID", 110), ("name", "Book Name", 260),
                        ("author", "Author", 200), ("category", "Category", 160)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        for r in db.fetch_all(
                "SELECT book_id, book_name, author, category FROM library "
                "WHERE availability='Available' ORDER BY book_id"):
            tree.insert("", "end", values=(r["book_id"], r["book_name"],
                                           r.get("author"), r.get("category")))

    def _tab_issued(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Issued Books  ")
        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=12)
        cols = ("bid", "name", "issued_to", "issue", "due", "fine")
        tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("bid", "Book ID", 100), ("name", "Book Name", 200),
                        ("issued_to", "Issued To", 120), ("issue", "Issue Date", 130),
                        ("due", "Due Date", 130), ("fine", "Est. Fine", 100)]:
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        for r in db.fetch_all(
                "SELECT * FROM library WHERE availability='Issued' ORDER BY book_id"):
            fine = compute_fine(r.get("issue_date"))
            tree.insert("", "end", values=(
                r["book_id"], r["book_name"], r.get("issued_to"),
                r.get("issue_date"), r.get("return_date"), f"₹{fine}",
            ))
