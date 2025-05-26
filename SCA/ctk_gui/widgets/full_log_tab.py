from __future__ import annotations
import pathlib, io
import customtkinter as ctk
from tkinter import filedialog
from ctk_gui.ui_theme.utils.style_utils import get_theme_colors
from ctk_gui.widgets._job_tracker import JobTracker

# Path to the secure_chat server log
LOG_PATH = pathlib.Path(__file__).resolve().parents[2] / "logs" / "secure_chat.log"

class FullLogTab(JobTracker):
    """
    Live viewer that first loads *all* existing log entries, then tails new ones.
    """
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Card background
        colors = get_theme_colors()
        card_color = colors["fg"]
        self.card = ctk.CTkFrame(self, corner_radius=12, fg_color=card_color)
        self.card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Toolbar with Pause/Save
        bar = ctk.CTkFrame(self.card, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="w")
        self.btn_pause = ctk.CTkButton(bar, text="Pause", width=100, height=30,
                                        font=(None, 12, "bold"), corner_radius=6,
                                        command=self._toggle_pause)
        self.btn_save  = ctk.CTkButton(bar, text="Save log …", width=100, height=30,
                                        font=(None, 12, "bold"), corner_radius=6,
                                        command=self._save_dialog)
        self.btn_pause.pack(side="left", padx=(0,8))
        self.btn_save.pack(side="left")

        # Text area for logs
        self.out = ctk.CTkTextbox(self.card, state="disabled", wrap="none",
                                  font=("Bahnschrift Condensed", 16))
        self.out.grid(row=1, column=0, sticky="nsew", pady=(8,0))
        self.card.grid_rowconfigure(1, weight=1)
        self.card.grid_columnconfigure(0, weight=1)

        # File and state
        self._file = None
        self._paused = False

        # Open and read everything, then start tailing
        self._open_file()
        self._after_poll = self.schedule(300, self._poll_file)

    def update_theme(self):
        """Re-apply theme colors when mode changes."""
        colors = get_theme_colors()
        self.card.configure(fg_color=colors["fg"])
        self.out.configure(fg_color=colors["fg"], text_color=colors["text"])

    def _open_file(self):
        try:
            # Open log and read all existing content
            self._file = LOG_PATH.open("r", encoding="utf-8", errors="replace")
            content = self._file.read()
            for line in content.splitlines():
                self._append(line)
            # Seek to end for new entries
            self._file.seek(0, io.SEEK_END)
        except Exception as exc:
            self._append(f"[FullLogTab] Cannot open {LOG_PATH}: {exc}")
            self._file = None

    def _poll_file(self):
        if self._file and not self._paused:
            where = self._file.tell()
            line = self._file.readline()
            if not line:
                self._file.seek(where)
            else:
                self._append(line.rstrip())
        # Schedule next poll
        self._after_poll = self.schedule(300, self._poll_file)

    def _append(self, txt: str):
        """Append a line to the textbox, scrolling to end."""
        self.out.configure(state="normal")
        self.out.insert("end", txt + "\n")
        self.out.configure(state="disabled")
        self.out.see("end")

    def _toggle_pause(self):
        """Pause or resume tailing new entries."""
        self._paused = not self._paused
        self.btn_pause.configure(text=("Resume" if self._paused else "Pause"))

    def _save_dialog(self):
        """Save current textbox content to a file."""
        file = filedialog.asksaveasfilename(defaultextension=".log",
                                            initialfile="secure_chat_full.log")
        if file:
            with open(file, "w", encoding="utf-8") as f:
                f.write(self.out.get("1.0", "end-1c"))
