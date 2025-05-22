"""
LogTab
======

Live tail of logs/secure_chat.log with Pause / Save.
Now wrapped in a centred card that stretches with the window.
"""

from __future__ import annotations
import pathlib, io
import customtkinter as ctk
from tkinter import filedialog
from ctk_gui.ui_theme.utils import style_utils
from ctk_gui.ui_theme.utils.style_utils import get_theme_colors
from ctk_gui.widgets._job_tracker import JobTracker

LOG_PATH = pathlib.Path(__file__).resolve().parents[2] / "logs" / "secure_chat.log"


class LogTab(JobTracker):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)

        # Make this frame fill the content area
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Theme-aware card background
        colors = get_theme_colors()
        card_color = colors["fg"]

        # Single card that stretches
        self.card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=card_color
        )
        self.card.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")

        self._after_poll = self.schedule(300, self._poll_file)

        # Allow the log viewer (row 1) to expand inside the card
        self.card.grid_rowconfigure(1, weight=1)
        self.card.grid_columnconfigure(0, weight=1)

        # Toolbar
        bar = ctk.CTkFrame(self.card, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="w")

        self.btn_pause = ctk.CTkButton(
            bar,
            text="Pause",
            width=175,
            height=36,
            anchor="center",
            hover_color="#188781",
            font=("Cascadia Code", 14, "bold"),
            corner_radius=6,
            command=self._toggle_pause
        )
        self.btn_save = ctk.CTkButton(
            bar,
            text="Save log …",
            width=175,
            height=36,
            anchor="center",
            hover_color="#188781",
            font=("Cascadia Code", 15, "bold"),
            corner_radius=6,
            command=self._save_dialog
        )
        self.btn_pause.pack(side="left", padx=(0, 8))
        self.btn_save.pack(side="left")

        # Log viewer
        self.out = ctk.CTkTextbox(
            self.card,
            state="disabled",
            wrap="none",
            font=("Bahnschrift Condensed",20)
        )
        self.out.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        # File tailer setup
        self._file: io.TextIOWrapper | None = None
        self._paused = False
        self._open_file()
        
        

    # ---------------------------------------------------------------- tailer
    def update_theme(self):
        # re-apply card bg
        colors = get_theme_colors()
        self.card.configure(fg_color=colors["fg"])
        # re-apply textbox bg & text color
        self.out.configure(
            fg_color=colors["fg"],
            text_color=colors["text"]
        )
    def _open_file(self):
        try:
            self._file = LOG_PATH.open("r", encoding="utf-8", errors="replace")
            self._file.seek(0, io.SEEK_END)
        except Exception as exc:
            self._append(f"[LogTab] Cannot open {LOG_PATH}: {exc}")
            self._file = None

    def _poll_file(self):
        if self._file and not self._paused:
            where = self._file.tell()
            line  = self._file.readline()
            if not line:
                self._file.seek(where)
            else:
                self._append(line.rstrip())
        self._after_poll = self.schedule(300, self._poll_file)

    # ---------------------------------------------------------------- append
    def _append(self, txt: str):
        self.out.configure(state="normal")
        self.out.insert("end", txt + "\n")
        self.out.configure(state="disabled")
        self.out.see("end")

    # ---------------------------------------------------------------- slots
    def _toggle_pause(self):
        self._paused = not self._paused
        self.btn_pause.configure(text=("Resume" if self._paused else "Pause"))

    def _save_dialog(self):
        file = filedialog.asksaveasfilename(defaultextension=".log",
                                            initialfile="secure_chat_demo.log")
        if file:
            with open(file, "w", encoding="utf-8") as f:
                f.write(self.out.get("1.0", "end-1c"))
