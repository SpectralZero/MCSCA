"""
ui.shredder_dialogs
───────────────────
Self-contained CTk GUI wrapper around core.secure_delete.

Call `open_shredding_menu(parent)` from your main app.
"""

from __future__ import annotations

import threading
import logging
from pathlib import Path
from typing import Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.secure_delete import shred_file, shred_directory  # adjust import path!

LOG = logging.getLogger("shredder_gui")
LOG.addHandler(logging.NullHandler())

def new_toplevel(
    parent: ctk.CTk | ctk.CTkToplevel,
    title: str,
    geometry: str,
    modal: bool = True,
    topmost_once: bool = True,
) -> ctk.CTkToplevel:
    """Return a prepared CTkToplevel that will appear in front of *parent*."""
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry(geometry)
    win.transient(parent)     # keep stacking order
    win.lift()                # raise above siblings
    if topmost_once:
        win.attributes("-topmost", True)
        # release topmost after the first idle loop so it doesn't annoy the user
        win.after_idle(lambda: win.attributes("-topmost", False))
    if modal:
        win.grab_set()        # block interaction with parent until closed
    win.focus_force()
    return win

# ════════════════════════════════════════════════════════════════════════════════
# High-level menu
# ════════════════════════════════════════════════════════════════════════════════
def open_shredding_menu(master: ctk.CTk):
    win = new_toplevel(master, "Secure Shredder", "480x360")
    win.resizable(False, False)

    ctk.CTkLabel(win, text="Secure Shredder", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=18)
    for txt, cmd in (
        ("Shred FILE …", lambda: _file_dialog(win)),
        ("Shred DIRECTORY …", lambda: _dir_dialog(win)),
    ):
        ctk.CTkButton(win, text=txt, width=220, height=42, command=cmd).pack(pady=14)

    ctk.CTkButton(win, text="Close", width=120, command=win.destroy).pack(pady=26)


# ════════════════════════════════════════════════════════════════════════════════
# Dialog helpers
# ════════════════════════════════════════════════════════════════════════════════
def _file_dialog(master):
    path = filedialog.askopenfilename(title="Select file to shred")
    if not path:
        return
    passes, keep = _ask_opts(master, save_default=True)
    if passes is None:
        return
    if not messagebox.askyesno("Confirm", f"Shred {Path(path).name} with {passes} passes?"):
        return
    _run_thread(
        master,
        target=_shred_file_thread,
        args=(path, passes, keep),
        title="Shredding File…",
    )


def _dir_dialog(master):
    path = filedialog.askdirectory(title="Select directory to shred")
    if not path:
        return
    passes, keep = _ask_opts(master, is_dir=True)
    if passes is None:
        return
    if not messagebox.askyesno(
        "Confirm", f"Shred directory '{Path(path).name}' with {passes} passes?"
    ):
        return
    _run_thread(
        master,
        target=_shred_dir_thread,
        args=(path, passes, keep),
        title="Shredding Directory…",
    )


def _ask_opts(master, *, is_dir=False, save_default=False) -> Tuple[int | None, bool]:
    dlg = dlg = new_toplevel(master, "Shred Options", "320x210")
    dlg.resizable(False, False)

    ctk.CTkLabel(dlg, text="Overwrite passes (1-35):").pack(pady=12)
    passes_var = ctk.StringVar(value="3")
    entry = ctk.CTkEntry(dlg, textvariable=passes_var, width=60)
    entry.pack()

    keep_var = ctk.BooleanVar(value=save_default)
    if is_dir or not save_default:
        ctk.CTkCheckBox(dlg, text="Keep garbled bytes (move instead of delete)", variable=keep_var).pack(
            pady=12
        )

    result = {"ok": False}

    def _ok():
        try:
            p = int(passes_var.get())
            if not 1 <= p <= 35:
                raise ValueError
            result["passes"] = p
            result["keep"] = bool(keep_var.get())
            result["ok"] = True
            dlg.destroy()
        except ValueError:
            messagebox.showerror("Invalid", "Enter an integer 1-35.")

    ctk.CTkButton(dlg, text="Confirm", command=_ok, width=90).pack(pady=18)
    dlg.wait_window()
    return (result["passes"], result["keep"]) if result["ok"] else (None, None)


# ════════════════════════════════════════════════════════════════════════════════
# Thread wrappers + progress GUI
# ════════════════════════════════════════════════════════════════════════════════
def _run_thread(master, target, args, title):
    prog = _ProgressWindow(master, title)
    th = threading.Thread(target=target, args=(*args, prog), daemon=True)
    th.start()



class _ProgressWindow:
    def __init__(self, master, title):
        self.win =  new_toplevel(master, title, "380x140", modal=False)
        self.win.resizable(False, False)
        ctk.CTkLabel(self.win, text=title, font=ctk.CTkFont(size=16)).pack(pady=10)
        self.bar = ctk.CTkProgressBar(self.win, width=300)
        self.bar.set(0)
        self.bar.pack(pady=10)

    # callback expected by secure_delete
    def update(self, cur, tot):
        self.bar.set(cur / tot)
        self.win.update_idletasks()

    def close(self):
        self.win.destroy()


def _shred_file_thread(path, passes, keep, prog: _ProgressWindow):
    ok, msg = shred_file(
        path,
        passes=passes,
        keep_bytes=keep,
        keep_root=_select_outdir() if keep else None,
        progress=prog.update,
    )
    prog.close()
    _final_popup(ok, msg)


def _shred_dir_thread(path, passes, keep, prog: _ProgressWindow):
    ok, msg = shred_directory(
        path,
        passes=passes,
        keep_bytes=keep,
        keep_root=_select_outdir() if keep else None,
        progress=prog.update,
    )
    prog.close()
    _final_popup(ok, msg)


def _select_outdir() -> str | None:
    out = filedialog.askdirectory(title="Destination for garbled files")
    return out or None


def _final_popup(ok: bool, msg: str):
    (messagebox.showinfo if ok else messagebox.showerror)("Shredder", msg)
    LOG.info(msg if ok else f"FAIL: {msg}")
