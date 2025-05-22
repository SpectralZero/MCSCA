#!/usr/bin/env python3
"""
wipe_button.py  ──  A ready-made “Exit & Wipe” sidebar button.
• Works with any root window (CTk)
• Pops a confirmation MessageBox
"""
from __future__ import annotations
import customtkinter as ctk, sys
from tools.wipe_manager import CleanupManager

def add_exit_button(sidebar:ctk.CTkFrame, root_window:ctk.CTk):
    mgr = CleanupManager()              # ensure singleton alive

    def _on_click():
        if ctk.CTkMessagebox(
            title="Exit & Wipe",
            message="Close Secure-Chat and erase all traces?",
            icon="warning",
            option_1="Yes", option_2="No").get() == "Yes":
            mgr.wipe()
            root_window.destroy()
            sys.exit(0)

    btn = ctk.CTkButton(
        sidebar, text=" Exit & Wipe",
        fg_color="#912626", hover_color="#B93535",
        command=_on_click, anchor="w"
    )
    btn.pack(fill="x", pady=6, padx=6)
    return btn
