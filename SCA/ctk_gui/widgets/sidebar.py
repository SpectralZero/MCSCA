"""
Collapsible sidebar widget used by the launcher.

Instantiate with a dict  {page_name: callback}  where the callback switches
the main stack to that page.
"""

from __future__ import annotations
import customtkinter as ctk
from ctk_gui.widgets.side_button import SideButton


class Sidebar(ctk.CTkFrame):
    WIDTH_EXPANDED = 200
    WIDTH_COLLAPSED = 60

    def __init__(self, master, routes: dict[str, callable], **kw):
        """
        routes = {
            "Server":   lambda: show("Server"),
            "Clients":  lambda: show("Clients"),
            ...
        }
        """
        super().__init__(master, width=self.WIDTH_COLLAPSED, corner_radius=0, **kw)
        self.expanded = False
        self._routes  = routes

        # hamburger toggle at the top
        self._toggle_btn = SideButton(
            self, "menu.svg", "Toggle sidebar", self.toggle
        )
        self._toggle_btn.grid(row=0, column=0, pady=(6, 2))

        # nav buttons
        self._buttons: dict[str, SideButton] = {}
        for idx, (name, cb) in enumerate(routes.items(), start=1):
            b = SideButton(self, f"{name.lower()}.svg", name, cb)
            b.grid(row=idx, column=0, pady=2)
            self._buttons[name] = b

        self.grid_rowconfigure(idx + 1, weight=1)

    # ---------------------------------------------------------------- toggle
    def toggle(self):
        self.expanded = not self.expanded
        new_w = self.WIDTH_EXPANDED if self.expanded else self.WIDTH_COLLAPSED
        self.configure(width=new_w)

        # show / hide button tooltips (text) by toggling text attribute
        for name, btn in self._buttons.items():
            btn.configure(text=name if self.expanded else "")
