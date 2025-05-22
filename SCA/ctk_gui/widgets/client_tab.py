# ctk_gui/widgets/client_tab.py
"""
ClientTab
=========
Tab for launching/killing and filtering multiple demo clients
and launching the Admin GUI in a responsive, theme-aware card.
"""
from __future__ import annotations
import subprocess, os, queue, threading, signal, sys
import pathlib
import customtkinter as ctk
from tkinter import ttk, messagebox
from ctk_gui.common import PY312, CHAT_DIR
from ctk_gui.ui_theme.utils.style_utils import get_theme_colors
from ctk_gui.widgets._job_tracker import JobTracker

class ClientTab(JobTracker):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)

        # allow this frame to expand
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # theme-aware card
        colors = get_theme_colors()
        self.card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=colors["fg"]
        )
        self.card.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")

        # configure internal grid
        self.card.grid_rowconfigure(3, weight=1)
        self.card.grid_columnconfigure(0, weight=1)

        # discover scripts
        root = CHAT_DIR
        self.cfg: dict[str, tuple[pathlib.Path, int]] = {
            "Client 1": (root/"secure_chat_client1.py", 12346),
            "Client 2": (root/"secure_chat_client2.py", 12347),
            "Client 3": (root/"secure_chat_client3.py", 12348),
        }
        self._procs: dict[str, subprocess.Popen[str]] = {}
        self._q: queue.Queue[tuple[str, str]] = queue.Queue()

        self._after_id = self.schedule(300, self._poll_queue)

        
        # toolbar
        bar = ctk.CTkFrame(self.card, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="w", pady=(0,6))

        def pill(txt, clr, cmd):
            return ctk.CTkButton(
                bar,
                text=txt,
                fg_color=clr,
                width=95,
                corner_radius=6,
                command=cmd
            )
        pill("Launch",    "#424242", self.launch_selected).pack(side="left", padx=4)
        pill("Launch All","#2e7d32", self.launch_all).pack(side="left", padx=4)
        pill("Kill",      "#c62828", self.kill_selected).pack(side="left", padx=4)
        
        # Admin button launches external admin.py GUI
        pill("Admin",     "#8e24aa", self.launch_admin).pack(side="left", padx=4)

        # filter row
        flt = ctk.CTkFrame(self.card, fg_color="transparent")
        flt.grid(row=1, column=0, sticky="ew")
        flt.grid_columnconfigure(2, weight=1)

        self.combo_client = ctk.CTkOptionMenu(flt, values=["ALL"]+list(self.cfg))
        self.combo_state  = ctk.CTkOptionMenu(flt, values=["ALL","idle","running","exited","killed"])
        self.search       = ctk.CTkEntry(flt, placeholder_text="Search…")

        self.combo_client.grid(row=0, column=0, padx=(0,4))
        self.combo_state .grid(row=0, column=1, padx=4)
        self.search      .grid(row=0, column=2, padx=(4,0), sticky="ew")

        for w in (self.combo_client, self.combo_state):
            w.configure(command=lambda *_: self._apply_filter())
        self.search.bind("<KeyRelease>", lambda *_: self._apply_filter())

        # table frame
        tbl_frm = ctk.CTkFrame(self.card, fg_color="transparent")
        tbl_frm.grid(row=3, column=0, sticky="nsew")
        tbl_frm.grid_rowconfigure(0, weight=1)
        tbl_frm.grid_columnconfigure(0, weight=1)

        cols = ("pid","client","state")
        self.tree = ttk.Treeview(tbl_frm, columns=cols, show="headings")
        for c,w in zip(cols, (90,160,90)):
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=w, anchor="w", stretch=True)

        ysb = ttk.Scrollbar(tbl_frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")

        for name in self.cfg:
            self.tree.insert("", "end", iid=name, values=("", name, "idle"))

        # schedule polling
        self._after_id = self.after(300, self._poll_queue)

    def launch_admin(self):
        """
        Launch the external Admin GUI as a separate process.
        """
        admin_script = CHAT_DIR / "admin.py"
        subprocess.Popen([sys.executable, str(admin_script)], cwd=str(CHAT_DIR))

    def update_theme(self):
        """
        Re-apply card background on theme change.
        """
        colors = get_theme_colors()
        self.card.configure(fg_color=colors["fg"])

    

    # spawning/killing processes
    def _spawn(self, iid: str) -> None:
        if self.tree.set(iid, "pid"): return
        script, port = self.cfg[iid]
        env = os.environ.copy(); env["PYTHONUTF8"] = "1"
        proc = subprocess.Popen(
            [PY312, str(script), "localhost", "4444", str(port)],
            cwd=str(CHAT_DIR), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        self._procs[iid] = proc
        self.tree.item(iid, values=(proc.pid, iid, "running"))
        threading.Thread(target=self._reader, args=(iid,proc), daemon=True).start()

    def launch_selected(self):
        if not self.tree.selection():
            messagebox.showinfo("Nothing selected","Select one or more rows.")
            return
        for iid in self.tree.selection(): self._spawn(iid)

    def launch_all(self):    [self._spawn(i) for i in self.cfg]
    def kill_selected(self):
        for iid in self.tree.selection():
            p = self._procs.pop(iid, None)
            if p and p.poll() is None:
                if os.name == 'nt': p.terminate()
                else: p.send_signal(signal.SIGINT)
            self.tree.item(iid, values=("", iid, "killed"))

    

    def _apply_filter(self):
        clt, st, pat = self.combo_client.get(), self.combo_state.get(), self.search.get().lower()
        for iid in self.cfg:
            pid, client, state = self.tree.item(iid, "values")
            visible = (
                (clt=="ALL" or client==clt) and
                (st =="ALL" or state ==st) and
                (not pat or pat in client.lower())
            )
            self.tree.detach(iid) if not visible else self.tree.reattach(iid, "", "end")

    def _reader(self, iid: str, proc: subprocess.Popen[str]) -> None:
        assert proc.stdout
        for ln in proc.stdout:
            self._q.put((iid, ln.rstrip()))
        self._q.put((iid, "[exited]"))

    def _poll_queue(self):
        try:
            while True:
                iid, line = self._q.get_nowait()
                if "[exited]" in line:
                    self.tree.item(iid, values=("", iid, "exited"))
        except queue.Empty:
            pass
        # reschedule
        self._after_id = self.schedule(300, self._poll_queue)
