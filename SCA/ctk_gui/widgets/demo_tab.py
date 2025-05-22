import os
import sys
import subprocess
from pathlib import Path
import customtkinter as ctk
from ctk_gui.common import VID
from tkinter import messagebox

# Path to the demo video
VIDEO_PATH = VID

class DemoTab(ctk.CTkFrame):
    """
    DemoTab that delegates playback to the OS default video player.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Provide user feedback in the UI
        
        
        info = ctk.CTkLabel(
            self,
            text="Click 'DEMO' again to open the TLS demo in your system's video player.",
            wraplength=600,
            font=ctk.CTkFont(family="System", size=26, weight="bold"),
            justify="center"
        )
        info.pack(expand=True, fill="both", padx=20, pady=20)

    def load_and_play(self):
        # Check existence
        if not VIDEO_PATH.exists():
            messagebox.showerror(
                "File Not Found",
                f"Cannot find demo video:\n{VIDEO_PATH}"
            )
            return

        # On Windows, os.startfile will use the default player
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(VIDEO_PATH))
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(VIDEO_PATH)])
            else:
                subprocess.Popen(["xdg-open", str(VIDEO_PATH)])
        except Exception as e:
            messagebox.showerror(
                "Playback Error",
                f"Could not launch video:\n{e}"
            )