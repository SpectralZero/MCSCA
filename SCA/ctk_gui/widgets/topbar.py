"""
TopBar
======

Simple application bar that shows the branded title on the left and
optional action buttons (e.g. notification, dark/light toggle) on the right.
"""

from __future__ import annotations
import customtkinter as ctk
from ctk_gui.widgets.side_button import SideButton
from ctk_gui.theme import FONT_BODY


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_toggle_theme: callable, **kw):
        super().__init__(master, height=36, corner_radius=0, **kw)

        # title on the left
        ctk.CTkLabel(
            self, text=" SecureChatApp", font=FONT_BODY
        ).pack(side="left", padx=8)

        # spacer
        ctk.CTkLabel(self, text="").pack(side="left", expand=True)

        # right‑side buttons
        SideButton(self, "bell.svg",  "Notifications", lambda: None
                   ).pack(side="right", padx=(0,4))
        SideButton(self, "moon.svg",  "Toggle theme",   on_toggle_theme
                   ).pack(side="right", padx=(0,8))
