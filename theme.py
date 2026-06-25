"""
theme.py
========
Centralized theme constants and reusable widget styles for CampusHub.

Every GUI module imports from here so the look-and-feel stays consistent
(dark theme, glassmorphism-style cards, rounded buttons, hover effects).
"""

import tkinter as tk
from tkinter import ttk


# -----------------------------------------------------------------------------
# Color palette (Modern Dark Theme)
# -----------------------------------------------------------------------------
BG_PRIMARY = "#0f1117"        # main window background
BG_SECONDARY = "#1a1d29"      # sidebar / panels
BG_CARD = "#1f2333"           # glassmorphism card surface
BG_CARD_HOVER = "#262b3f"     # card hover
BG_INPUT = "#2a2f45"          # entry fields
BG_ACCENT = "#6c5ce7"         # primary accent (purple)
BG_ACCENT_HOVER = "#7f70f0"
BG_SUCCESS = "#00b894"
BG_DANGER = "#e74c3c"
BG_WARNING = "#f39c12"
BG_INFO = "#0984e3"

FG_PRIMARY = "#ffffff"        # main text
FG_SECONDARY = "#b2b8d4"      # muted text
FG_MUTED = "#7a83a6"

BORDER_COLOR = "#2d3148"

# Stat card colors (for dashboard cards)
CARD_COLORS = [
    ("#6c5ce7", "#a29bfe"),   # purple
    ("#00b894", "#55efc4"),   # green
    ("#0984e3", "#74b9ff"),   # blue
    ("#e17055", "#fab1a0"),   # orange
    ("#fdcb6e", "#ffeaa7"),   # yellow
    ("#e84393", "#fd79a8"),   # pink
    ("#00cec9", "#81ecec"),   # teal
    ("#6c5ce7", "#a29bfe"),   # purple
]

# Fonts
FONT_TITLE = ("Segoe UI Semibold", 22, "bold")
FONT_SUBTITLE = ("Segoe UI Semibold", 16, "bold")
FONT_HEADING = ("Segoe UI Semibold", 13, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_BODY_BOLD = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_BUTTON = ("Segoe UI Semibold", 11, "bold")
FONT_STAT_VALUE = ("Segoe UI Semibold", 24, "bold")
FONT_STAT_LABEL = ("Segoe UI", 10)


# -----------------------------------------------------------------------------
# Default window geometry
# -----------------------------------------------------------------------------
DEFAULT_GEOMETRY = "1280x780"


def apply_theme(root: tk.Tk) -> None:
    """Apply the base dark theme to the root window."""
    root.configure(bg=BG_PRIMARY)
    root.option_add("*Background", BG_PRIMARY)
    root.option_add("*Foreground", FG_PRIMARY)
    root.option_add("*Font", FONT_BODY)
    # Global ttk style baseline
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    configure_ttk_style(style)


def configure_ttk_style(style: ttk.Style) -> None:
    """Configure ttk widget styles (treeview, combo, etc.)."""
    style.configure("TFrame", background=BG_PRIMARY)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("Sidebar.TFrame", background=BG_SECONDARY)

    style.configure("TLabel", background=BG_PRIMARY, foreground=FG_PRIMARY, font=FONT_BODY)
    style.configure("Card.TLabel", background=BG_CARD, foreground=FG_PRIMARY)
    style.configure("Sidebar.TLabel", background=BG_SECONDARY, foreground=FG_SECONDARY)
    style.configure("Muted.TLabel", background=BG_PRIMARY, foreground=FG_MUTED)
    style.configure("Title.TLabel", background=BG_PRIMARY, foreground=FG_PRIMARY,
                    font=FONT_TITLE)
    style.configure("Subtitle.TLabel", background=BG_PRIMARY, foreground=FG_PRIMARY,
                    font=FONT_SUBTITLE)

    # Treeview (used for tables across modules)
    style.configure("Treeview",
                    background=BG_CARD,
                    fieldbackground=BG_CARD,
                    foreground=FG_PRIMARY,
                    rowheight=28,
                    font=FONT_BODY)
    style.configure("Treeview.Heading",
                    background=BG_ACCENT,
                    foreground=FG_PRIMARY,
                    font=FONT_HEADING,
                    relief="flat")
    style.map("Treeview",
              background=[("selected", BG_ACCENT)],
              foreground=[("selected", FG_PRIMARY)])

    # Combobox
    style.configure("TCombobox",
                    fieldbackground=BG_INPUT,
                    background=BG_INPUT,
                    foreground=FG_PRIMARY,
                    arrowcolor=FG_PRIMARY)
    style.map("TCombobox",
              fieldbackground=[("readonly", BG_INPUT)],
              foreground=[("readonly", FG_PRIMARY)])

    # Notebook tabs
    style.configure("TNotebook", background=BG_PRIMARY, borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=BG_CARD,
                    foreground=FG_SECONDARY,
                    padding=(18, 10),
                    font=FONT_BODY_BOLD)
    style.map("TNotebook.Tab",
              background=[("selected", BG_ACCENT)],
              foreground=[("selected", FG_PRIMARY)])


# -----------------------------------------------------------------------------
# Reusable widgets
# -----------------------------------------------------------------------------
class RoundedButton(tk.Canvas):
    """
    A rounded button drawn on a Canvas with hover effect.
    Falls back gracefully and needs no PIL dependency.
    """

    def __init__(self, parent, text, command=None, width=160, height=42,
                 bg=BG_ACCENT, fg=FG_PRIMARY, hover_bg=BG_ACCENT_HOVER,
                 font=FONT_BUTTON, radius=20, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"], highlightthickness=0, **kwargs)
        self.command = command
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg
        self.radius = radius
        self.current_bg = bg

        self._draw(self.bg)
        self.text_id = self.create_text(width // 2, height // 2,
                                        text=text, fill=fg, font=font)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, color):
        w = int(self["width"])
        h = int(self["height"])
        r = self.radius
        self.delete("round")
        self.create_round_rect(2, 2, w - 2, h - 2, r, fill=color,
                               outline="", tags="round")

    def create_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        """Draw a rounded rectangle using a polygon path."""
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, _):
        self._draw(self.hover_bg)
        self.current_bg = self.hover_bg
        self.config(cursor="hand2")

    def _on_leave(self, _):
        self._draw(self.bg)
        self.current_bg = self.bg
        self.config(cursor="")

    def _on_click(self, _):
        if self.command:
            self.command()


class StatCard(tk.Frame):
    """
    Dashboard statistics card with a colored gradient-style header.
    Shows a title, a big value, and an optional subtitle.
    """

    def __init__(self, parent, title, value="0", subtitle="", color_pair=None,
                 icon="", **kwargs):
        super().__init__(parent, bg=BG_CARD, **kwargs)
        self.color_pair = color_pair or CARD_COLORS[0]
        self.configure(highlightbackground=BORDER_COLOR,
                       highlightthickness=1, bd=0)

        # Top color strip
        strip = tk.Frame(self, bg=self.color_pair[0], height=6)
        strip.pack(side="top", fill="x")

        body = tk.Frame(self, bg=BG_CARD)
        body.pack(fill="both", expand=True, padx=18, pady=14)

        tk.Label(body, text=title, bg=BG_CARD, fg=FG_SECONDARY,
                 font=FONT_STAT_LABEL, anchor="w").pack(fill="x")

        self.value_lbl = tk.Label(body, text=value, bg=BG_CARD,
                                  fg=FG_PRIMARY, font=FONT_STAT_VALUE, anchor="w")
        self.value_lbl.pack(fill="x", pady=(4, 0))

        if subtitle:
            tk.Label(body, text=subtitle, bg=BG_CARD, fg=self.color_pair[0],
                     font=FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 0))

        # Hover effect
        self.bind_sequence()
        for child in self.winfo_children():
            child.bind("<Enter>", lambda e: self._hover(True))
            child.bind("<Leave>", lambda e: self._hover(False))

    def bind_sequence(self):
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, state):
        self.configure(bg=BG_CARD_HOVER if state else BG_CARD)

    def set_value(self, value):
        self.value_lbl.config(text=str(value))


def make_entry(parent, placeholder="", show=None, width=28):
    """Create a styled dark entry widget."""
    entry = tk.Entry(parent, width=width, bg=BG_INPUT, fg=FG_PRIMARY,
                     insertbackground=FG_PRIMARY, relief="flat",
                     font=FONT_BODY, highlightthickness=1,
                     highlightbackground=BORDER_COLOR,
                     highlightcolor=BG_ACCENT, bd=8)
    if show:
        entry.config(show=show)
    if placeholder:
        entry.insert(0, placeholder)
        entry.config(fg=FG_MUTED)
        entry.bind("<FocusIn>", lambda e: _clear_placeholder(entry, placeholder))
        entry.bind("<FocusOut>", lambda e: _add_placeholder(entry, placeholder))
    return entry


def _clear_placeholder(entry, placeholder):
    if entry.get() == placeholder:
        entry.delete(0, tk.END)
        entry.config(fg=FG_PRIMARY)


def _add_placeholder(entry, placeholder):
    if not entry.get():
        entry.insert(0, placeholder)
        entry.config(fg=FG_MUTED)


def make_label(parent, text, bold=False, fg=FG_SECONDARY, bg=BG_PRIMARY, size=None):
    """Create a styled label."""
    font = (FONT_BODY_BOLD if bold else FONT_BODY)
    if size:
        font = ("Segoe UI Semibold" if bold else "Segoe UI", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, anchor="w")


def center_window(window, width=None, height=None):
    """Center a Tk window on screen."""
    window.update_idletasks()
    w = width or window.winfo_width()
    h = height or window.winfo_height()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    window.geometry(f"{w}x{h}+{x}+{y}")
