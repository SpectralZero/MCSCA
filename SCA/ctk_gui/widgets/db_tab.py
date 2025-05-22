from __future__ import annotations
import sqlite3
import pathlib
import customtkinter as ctk
from tkinter import ttk, messagebox
from ctk_gui.ui_theme.utils.style_utils import get_theme_colors
from ctk_gui.common import USERS_DB

# Path to the SQLite database
DB_PATH = USERS_DB

class DbTab(ctk.CTkFrame):
    """
    DbTab — view all columns from `users` in a responsive, full-width card.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Make this frame expand to fill content
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Theme-aware card container
        colors = get_theme_colors()
        self.card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=colors['fg'],
            border_width=1,
            border_color=colors.get('border', '#888888')
        )
        self.card.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")

        # Configure card grid: title (row 0), table (row 1), horizontal scrollbar (row 2)
        self.card.grid_rowconfigure(0, weight=0)
        self.card.grid_rowconfigure(1, weight=1)
        self.card.grid_rowconfigure(2, weight=0)
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_columnconfigure(1, weight=0)

        # Connect to DB
        try:
            self._conn = sqlite3.connect(DB_PATH)
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", f"Cannot open database:\n{e}")
            self._conn = None

        # Columns to display
        self._cols = [
            'id', 'username', 'password', 'role',
            'usb_serial', 'usb_hash', 'usb_fail_count', 'usb_locked_until'
        ]

        # Title
        ctk.CTkLabel(
            self.card,
            text="User Management",
            font=("Tahoma", 18),
            text_color=colors['text']
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(0,10))

        # Treeview setup
        self.tree = ttk.Treeview(
            self.card,
            columns=self._cols,
            show="headings"
        )
        for col in self._cols:
            heading = col.replace('_', ' ').title()
            self.tree.heading(col, text=heading)
            if col == 'id':
                self.tree.column(col, width=40, anchor='center')
            elif col in ('usb_fail_count', 'usb_locked_until'):
                self.tree.column(col, width=120, anchor='center')
            elif col == 'username':
                self.tree.column(col, width=160, anchor='w')
            else:
                self.tree.column(col, anchor='w')

        # Vertical scrollbar
        vsb = ttk.Scrollbar(
            self.card,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=(0,0))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0,0))

        # Horizontal scrollbar
        hsb = ttk.Scrollbar(
            self.card,
            orient="horizontal",
            command=self.tree.xview
        )
        self.tree.configure(xscrollcommand=hsb.set)
        hsb.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0,10))

        # Initial data load
        self._refresh()

    def _refresh(self) -> None:
        """
        Refresh table with all columns from `users`.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not self._conn:
            return
        query = f"SELECT {', '.join(self._cols)} FROM users ORDER BY id"
        cur = self._conn.execute(query)
        for rec in cur.fetchall():
            display = []
            for val in rec:
                if isinstance(val, (bytes, bytearray)):
                    hex_str = val.hex()
                    display.append(hex_str[:32] + '…')
                else:
                    display.append(str(val))
            self.tree.insert('', 'end', values=tuple(display))
    