#!/usr/bin/env python3
"""
tools.stego_dialogs  –  GOD-MODE v3
───────────────────────────────────
CustomTkinter GUI for LSB image steganography (hide / reveal plaintext).

Major features
• Live-resize preview (debounced, no flicker / crash)
• 500 × 500 thumbnail cap (memory-friendly)
• Global bottom button bar (always in view)
• Clipboard helpers, keyboard shortcuts
• Dark-mode friendly; easy accent colour tweak
• Robust error handling & logging (Python 3.12-ready)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from PIL import Image
from stegano import lsb
from tkinter import filedialog, messagebox

__all__ = ["open_stego_menu"]

LOG = logging.getLogger("stego_gui")
LOG.addHandler(logging.NullHandler())

# ────────────── tunables ──────────────
_PREVIEW_MAX = 500          # px – caps thumbnail size
_DEBOUNCE_MS = 120          # ms – resize debounce interval
_ACCENT      = "#3478f6"    # primary button colour
_FONT_CODE   = ("Segoe UI", 18)
_MIN_SIZE    = (960, 600)   # w, h – minimum window size
# ──────────────────────────────────────


# ════════════════════════════════════════════════════════════════════
def open_stego_menu(parent: ctk.CTk | ctk.CTkToplevel) -> None:
    """Launch the stego window (modal)."""
    win = _new_toplevel(parent, "Image Steganography", "960x700")
    _StegoWindow(win)


# ════════════════════════════════════════════════════════════════════
class _StegoWindow:
    # ────────────── init / layout ──────────────
    def __init__(self, win: ctk.CTkToplevel):
        self.win = win
        self.win.minsize(*_MIN_SIZE)

        # ── state ──
        self.orig_img: Optional[Image.Image] = None
        self.carrier:  Optional[Image.Image] = None
        self.carrier_path: Optional[str] = None
        self._preview_photo: Optional[ctk.CTkImage] = None
        self._resize_job: Optional[str] = None

        # ── top-level grid: content row (0) + button row (1) ──
        self.win.grid_rowconfigure(0, weight=1)
        self.win.grid_rowconfigure(1, weight=0)
        self.win.grid_columnconfigure((0, 1), weight=1, uniform="half")

        # ── left preview pane ───────────────────────────────
        left = ctk.CTkFrame(win, fg_color="#1f1f1f")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.img_label = ctk.CTkLabel(
            left, text="No image loaded",
            width=_PREVIEW_MAX, height=_PREVIEW_MAX, anchor="center"
        )
        self.img_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left.bind("<Configure>", self._on_resize)

        # ── right controls pane ─────────────────────────────
        right = ctk.CTkFrame(win, fg_color="#1f1f1f")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right, text="Message", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, pady=(12, 0))

        self.textbox = ctk.CTkTextbox(
            right, height=160, wrap="word", font=_FONT_CODE
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6, 6))

        # ── bottom button bar (row-1, spans both columns) ──
        btn_fr = ctk.CTkFrame(win, fg_color="#2a2a2a")
        btn_fr.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 10), padx=10)
        for i in range(6):
            btn_fr.grid_columnconfigure(i, weight=1)

        # helper to populate the bar
        def add(col, text, cmd, shortcut: str | None = None):
            btn = ctk.CTkButton(
                btn_fr, text=text, command=cmd,
                fg_color=_ACCENT, hover_color="#255dc4", width=110
            )
            btn.grid(row=0, column=col, padx=4, pady=2, sticky="ew")
            if shortcut:
                self.win.bind_all(shortcut, lambda _e: cmd())

        add(0, "Open Img",     self.open_image,  "<Control-o>")
        add(1, "Hide ➜ New",   self.hide_message)
        add(2, "Reveal",       self.reveal_message)
        add(3, "Save Carrier", self.save_carrier, "<Control-s>")
        add(4, "Copy",         self.copy_message, "<Control-c>")
        add(5, "Exit",         win.destroy,       "<Escape>")

        # close with window manager → call same destroy
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    # ────────────── resize handling ──────────────
    def _on_resize(self, _evt):
        if self._resize_job:
            self.win.after_cancel(self._resize_job)
        self._resize_job = self.win.after(
            _DEBOUNCE_MS,
            lambda: self._display_image(self.carrier or self.orig_img)
            if (self.carrier or self.orig_img) else None,
        )

    def _display_image(self, img: Optional[Image.Image]):
        if not img:
            return
        max_w = min(self.img_label.winfo_width()  or _PREVIEW_MAX, _PREVIEW_MAX)
        max_h = min(self.img_label.winfo_height() or _PREVIEW_MAX, _PREVIEW_MAX)
        preview = img.copy()
        preview.thumbnail((max_w, max_h))
        self._preview_photo = ctk.CTkImage(preview, size=preview.size)
        self.img_label.configure(image=self._preview_photo, text="")

    # ────────────── UI actions ──────────────
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose image",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with Image.open(path) as img_in:
                img_in.load()
                img = img_in.convert("RGB")
            self.orig_img = img
            self.carrier  = img.copy()
            self.carrier_path = path
            self.textbox.delete("1.0", "end")
            self._display_image(img)
        except Exception as exc:
            LOG.exception("open_image failed")
            messagebox.showerror("Image", f"Unable to open:\n{exc}")

    def hide_message(self):
        if not self.orig_img:
            messagebox.showwarning("Image", "Open an image first.")
            return
        plaintext = self.textbox.get("1.0", "end").rstrip("\n")
        if not plaintext:
            messagebox.showwarning("Text", "Nothing to hide.")
            return
        try:
            base = self.orig_img.copy(); base.load()
            self.carrier = lsb.hide(base, plaintext)
            self._display_image(self.carrier)
            self.textbox.delete("1.0", "end")
            messagebox.showinfo("Hide", "Message hidden in new carrier.")
        except Exception as exc:
            LOG.exception("hide_message failed")
            messagebox.showerror("Hide", f"Error:\n{exc}")

    def reveal_message(self):
        if not self.carrier:
            messagebox.showwarning("Image", "Open an image first.")
            return
        try:
            blob = lsb.reveal(self.carrier)
            if not blob:
                messagebox.showinfo("Reveal", "No hidden data found.")
                return
            self.textbox.delete("1.0", "end")
            self.textbox.insert("end", blob)
            messagebox.showinfo("Reveal", "Hidden message revealed.")
        except Exception as exc:
            LOG.exception("reveal_message failed")
            messagebox.showerror("Reveal", f"Error:\n{exc}")

    def save_carrier(self):
        if not self.carrier:
            messagebox.showwarning("Image", "Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            title="Save carrier image"
        )
        if not path:
            return
        try:
            img = self.carrier.copy(); img.load()
            img.save(path, format="PNG")
            messagebox.showinfo("Saved", f"Carrier saved to:\n{Path(path).name}")
        except Exception as exc:
            LOG.exception("save_carrier failed")
            messagebox.showerror("Save", f"Unable to save:\n{exc}")

    def copy_message(self):
        text = self.textbox.get("1.0", "end").rstrip("\n")
        if not text:
            messagebox.showinfo("Copy", "Nothing to copy.")
            return
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        messagebox.showinfo("Copy", "Message copied to clipboard.")


# ════════════════════════════════════════════════════════════════════
def _new_toplevel(parent, title: str, geom: str) -> ctk.CTkToplevel:
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry(geom)
    win.transient(parent)
    win.lift()
    win.attributes("-topmost", True)
    win.after_idle(lambda: win.attributes("-topmost", False))
    win.grab_set()        # modal
    win.focus_force()
    return win
