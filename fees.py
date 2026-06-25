"""
fees.py
=======
Fee management module for CampusHub.

Provides the FeesView frame with:
    - Fee structure (per-department default fee) and payment entry
    - Payment history per student
    - Pending fees overview
    - Simple receipt generation (text preview + optional save)
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date

from database import db
import theme


# Default annual fee per department (used when no records exist yet)
DEFAULT_FEE_STRUCTURE = {
    "Computer Science": 75000,
    "Electronics": 70000,
    "Mechanical": 65000,
    "Civil": 60000,
    "Management": 80000,
}


def generate_receipt_no() -> str:
    """Generate a unique receipt number."""
    count = db.fetch_one("SELECT COUNT(*) AS c FROM fees")["c"] + 1
    return f"RCP{datetime.now().strftime('%Y%m')}{count:04d}"


class FeesView(tk.Frame):
    """Admin panel for fee management."""

    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg=theme.BG_PRIMARY)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="💰  Fee Management",
                 bg=theme.BG_PRIMARY, fg=theme.FG_PRIMARY,
                 font=theme.FONT_TITLE).pack(anchor="w", padx=30, pady=(24, 0))
        tk.Label(self, text="Collect payments, view pending fees and generate receipts",
                 bg=theme.BG_PRIMARY, fg=theme.FG_MUTED,
                 font=theme.FONT_BODY).pack(anchor="w", padx=30)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=30, pady=20)
        self._tab_collect(nb)
        self._tab_pending(nb)
        self._tab_history(nb)

    # -------------------------------------------------------------------------
    # Collect payment tab
    # -------------------------------------------------------------------------
    def _tab_collect(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Collect Payment  ")

        form = tk.Frame(tab, bg=theme.BG_PRIMARY)
        form.pack(padx=20, pady=24)

        students = [f"{s['roll_no']} - {s['name']}"
                    for s in db.fetch_all("SELECT roll_no, name FROM students ORDER BY roll_no")]
        self.pay_stu = tk.StringVar()
        self.pay_amt = tk.StringVar()
        self.pay_status = tk.StringVar(value="Paid")

        fields = [("Student", "stu"), ("Amount (₹)", "amt"),
                  ("Status", "status")]
        widgets = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form, text=label, bg=theme.BG_PRIMARY,
                     fg=theme.FG_SECONDARY, font=theme.FONT_SMALL).grid(
                row=i, column=0, sticky="w", pady=6)
            if key == "stu":
                cb = ttk.Combobox(form, textvariable=self.pay_stu, values=students,
                                  state="readonly", width=30)
                cb.grid(row=i, column=1, pady=6, padx=8)
                widgets[key] = cb
            elif key == "status":
                cb = ttk.Combobox(form, textvariable=self.pay_status,
                                  values=["Paid", "Pending", "Partial"],
                                  state="readonly", width=30)
                cb.grid(row=i, column=1, pady=6, padx=8)
                widgets[key] = cb
            else:
                e = tk.Entry(form, textvariable=self.pay_amt, width=32,
                             bg=theme.BG_INPUT, fg=theme.FG_PRIMARY, relief="flat",
                             bd=6, font=theme.FONT_BODY, highlightthickness=1,
                             highlightbackground=theme.BORDER_COLOR,
                             highlightcolor=theme.BG_ACCENT)
                e.grid(row=i, column=1, pady=6, padx=8)
                widgets[key] = e

        theme.RoundedButton(tab, "💾 Record Payment", self.record_payment,
                            width=200, height=42).pack(pady=8)
        theme.RoundedButton(tab, "🧾 Generate Receipt", self.generate_receipt,
                            width=200, height=42, bg=theme.BG_INFO,
                            hover_bg="#3a9fde").pack(pady=4)

    def record_payment(self):
        sel = self.pay_stu.get()
        if not sel:
            messagebox.showwarning("Validation", "Please select a student.")
            return
        student_id = sel.split(" - ")[0]
        try:
            amount = float(self.pay_amt.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Enter a valid positive amount.")
            return
        status = self.pay_status.get()
        receipt = generate_receipt_no() if status == "Paid" else ""
        try:
            db.execute(
                "INSERT INTO fees (student_id, amount, payment_date, status, receipt_no) "
                "VALUES (?,?,?,?,?)",
                (student_id, amount, date.today().isoformat(), status, receipt),
            )
            db.log_activity(f"Recorded payment ₹{amount} from {student_id} ({status})")
            messagebox.showinfo("Success",
                                f"Payment recorded.\nReceipt No: {receipt or 'N/A'}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def generate_receipt(self):
        """Generate a printable text receipt for the latest payment of a student."""
        sel = self.pay_stu.get()
        if not sel:
            messagebox.showwarning("Validation", "Please select a student.")
            return
        student_id = sel.split(" - ")[0]
        row = db.fetch_one(
            "SELECT * FROM fees WHERE student_id = ? AND receipt_no != '' "
            "ORDER BY id DESC LIMIT 1", (student_id,)
        )
        if not row:
            messagebox.showinfo("Info", "No paid receipt found for this student.")
            return
        student = db.fetch_one("SELECT * FROM students WHERE roll_no = ?", (student_id,))

        lines = [
            "=" * 50,
            "          CAMPUZHUB - FEE RECEIPT",
            "=" * 50,
            f"Receipt No : {row['receipt_no']}",
            f"Date       : {row['payment_date']}",
            "-" * 50,
            f"Student    : {student.get('name', '')}",
            f"Roll No    : {student_id}",
            f"Department : {student.get('department', '')}",
            f"Semester   : {student.get('semester', '')}",
            "-" * 50,
            f"Amount Paid: Rs. {row['amount']:,.2f}",
            f"Status     : {row['status']}",
            "=" * 50,
            "           This is a computer generated receipt.",
            "=" * 50,
        ]
        text = "\n".join(lines)

        # Preview window
        win = tk.Toplevel(self)
        win.title(f"Receipt - {row['receipt_no']}")
        win.geometry("440x460")
        win.configure(bg=theme.BG_PRIMARY)
        win.transient(self)
        win.grab_set()
        theme.center_window(win, 440, 460)
        txt = tk.Text(win, bg=theme.BG_CARD, fg=theme.FG_PRIMARY, relief="flat",
                      font=("Consolas", 10), padx=20, pady=20, bd=0)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", text)
        txt.config(state="disabled")

        def save():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=f"receipt_{row['receipt_no']}.txt",
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("Saved", f"Receipt saved to:\n{path}", parent=win)

        theme.RoundedButton(win, "💾 Save as TXT", command=save,
                            width=180, height=38).pack(pady=12)

    # -------------------------------------------------------------------------
    # Pending fees tab
    # -------------------------------------------------------------------------
    def _tab_pending(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Pending Fees  ")
        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=12)
        cols = ("roll", "name", "dept", "amount", "status")
        self.pending_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("roll", "Roll No", 120), ("name", "Name", 200),
                        ("dept", "Department", 170), ("amount", "Amount", 120),
                        ("status", "Status", 110)]:
            self.pending_tree.heading(c, text=t)
            self.pending_tree.column(c, width=w, anchor="center")
        self.pending_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.pending_tree.yview)
        self.pending_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._load_pending()

    def _load_pending(self):
        for r in self.pending_tree.get_children():
            self.pending_tree.delete(r)
        rows = db.fetch_all(
            "SELECT f.student_id, s.name, s.department, f.amount, f.status "
            "FROM fees f LEFT JOIN students s ON s.roll_no = f.student_id "
            "WHERE f.status != 'Paid' ORDER BY f.student_id"
        )
        for r in rows:
            self.pending_tree.insert("", "end", values=(
                r["student_id"], r.get("name", ""), r.get("department", ""),
                f"₹{r['amount']:,.0f}", r["status"],
            ))
        if not rows:
            self.pending_tree.insert("", "end", values=(
                "—", "No pending fees 🎉", "", "", ""))

    # -------------------------------------------------------------------------
    # Payment history tab
    # -------------------------------------------------------------------------
    def _tab_history(self, nb):
        tab = tk.Frame(nb, bg=theme.BG_PRIMARY)
        nb.add(tab, text="  Payment History  ")

        controls = tk.Frame(tab, bg=theme.BG_PRIMARY)
        controls.pack(fill="x", padx=12, pady=12)
        tk.Label(controls, text="Student:", bg=theme.BG_PRIMARY,
                 fg=theme.FG_SECONDARY).pack(side="left", padx=4)
        students = [f"{s['roll_no']} - {s['name']}"
                    for s in db.fetch_all("SELECT roll_no, name FROM students ORDER BY roll_no")]
        self.hist_stu = ttk.Combobox(controls, values=students, state="readonly", width=30)
        self.hist_stu.pack(side="left", padx=4)
        theme.RoundedButton(controls, "🔍 View", self._load_history,
                            width=80, height=34).pack(side="left", padx=8)

        table = tk.Frame(tab, bg=theme.BG_PRIMARY)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        cols = ("date", "amount", "status", "receipt")
        self.hist_tree = ttk.Treeview(table, columns=cols, show="headings")
        for c, t, w in [("date", "Date", 180), ("amount", "Amount", 140),
                        ("status", "Status", 130), ("receipt", "Receipt No", 180)]:
            self.hist_tree.heading(c, text=t)
            self.hist_tree.column(c, width=w, anchor="center")
        self.hist_tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def _load_history(self):
        sel = self.hist_stu.get()
        if not sel:
            messagebox.showwarning("Validation", "Please select a student.")
            return
        student_id = sel.split(" - ")[0]
        for r in self.hist_tree.get_children():
            self.hist_tree.delete(r)
        rows = db.fetch_all(
            "SELECT amount, payment_date, status, receipt_no FROM fees "
            "WHERE student_id = ? ORDER BY payment_date DESC", (student_id,)
        )
        for r in rows:
            self.hist_tree.insert("", "end", values=(
                r["payment_date"], f"₹{r['amount']:,.0f}", r["status"],
                r.get("receipt_no") or "",
            ))
