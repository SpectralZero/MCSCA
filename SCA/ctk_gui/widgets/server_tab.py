"""
ServerTab
=========   (wrapped in a responsive, theme‑aware card)
"""

from __future__ import annotations
import subprocess, os, threading, queue, datetime, signal
import customtkinter as ctk
from ctk_gui.theme import FONT_BODY
from ctk_gui.common import PY312, CHAT_DIR
from ctk_gui.ui_theme.utils.style_utils import get_theme_colors
from ctk_gui.widgets._job_tracker import JobTracker

class ServerTab(JobTracker):
    PORT = 4444

    def __init__(self, master, **kw):
        super().__init__(master, **kw)

        # allow this frame to expand fully
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # create a theme‑aware card
        colors = get_theme_colors()
        self.card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=colors["fg"]
        )
        self.card.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")

        self._drain_job = self.schedule(200, self._drain_queue)
        
        # --- UI inside the card ---
        ctk.CTkLabel(
            self.card,
            text="Server Control",
            font=("System", 25)
        ).pack(anchor="w", pady=(0, 12))

        self.status = ctk.CTkLabel(
            self.card,
            text="Status: ⏹ Stopped",
            font=FONT_BODY
        )
        self.status.pack(anchor="w")

        btn_bar = ctk.CTkFrame(self.card, fg_color="transparent")
        btn_bar.pack(anchor="w", pady=8)

        self.start_btn = ctk.CTkButton(
            btn_bar,
            width=110,
            text="Start",
            command=self._start
        )
        self.stop_btn = ctk.CTkButton(
            btn_bar,
            width=110,
            text="Stop",
            command=self._stop,
            state="disabled"
        )
        self.start_btn.pack(side="left", padx=(0, 4))
        self.stop_btn.pack(side="left")

        self.tail = ctk.CTkTextbox(
            self.card,
            state="disabled",
            wrap="none",
            height=220,
            font=("Bahnschrift Condensed",20)
        )
        self.tail.pack(fill="both", expand=True, pady=(8, 0))

        # prepare for process control
        self._proc: subprocess.Popen[str] | None = None
        self._q: queue.Queue[str] = queue.Queue()
        self.after(200, self._drain_queue)

    def update_theme(self):
        """
        Re-apply the card background color after the global theme changes.
        """
        colors = get_theme_colors()
        self.card.configure(fg_color=colors["fg"])

    def _start(self):
        if self._proc and self._proc.poll() is None:
            return
        script = CHAT_DIR / "secure_chat_server.py"
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"

        self._proc = subprocess.Popen(
            [PY312, str(script), str(self.PORT)],
            cwd=str(CHAT_DIR), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        threading.Thread(target=self._reader, daemon=True).start()
        self._set_state(True)

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            # use terminate on Windows, SIGINT elsewhere
            if os.name == 'nt':
                self._proc.terminate()
            else:
                self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._set_state(False)

    def _set_state(self, running: bool):
        text = '🟢 Running' if running else '⏹ Stopped'
        self.status.configure(text=f"Status: {text}")
        self.start_btn.configure(state=("disabled" if running else "normal"))
        self.stop_btn.configure(state=("normal" if running else "disabled"))

    def _reader(self):
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            self._q.put(line.rstrip())
        self._q.put("[Server] exited")

    def _drain_queue(self):
        try:
            while True:
                ln = self._q.get_nowait()
                self._append(ln)
        except queue.Empty:
            pass
        self._drain_job = self.schedule(200, self._drain_queue)

    def _append(self, txt: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.tail.configure(state="normal")
        self.tail.insert("end", f"[{ts}] {txt}\n")
        self.tail.configure(state="disabled")
        self.tail.see("end")

    @property
    def is_running(self):
        return self._proc and self._proc.poll() is None

    @property
    def port(self):
        return self.PORT