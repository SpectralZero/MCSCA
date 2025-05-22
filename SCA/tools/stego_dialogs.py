"""
tools.stego_dialogs  (LSB-only version)
────────────────────────────────────────
Small CustomTkinter GUI to hide plain text inside an image (LSB) and reveal it.
No additional encryption layer – the chat’s TLS + encrypt_message()
already gives confidentiality in transit.

Usage:  open_stego_menu(parent: ctk.CTk | ctk.CTkToplevel)
"""

from __future__ import annotations
import io, os, logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from stegano import lsb

LOG = logging.getLogger("stego_gui")
LOG.addHandler(logging.NullHandler())


# ════════════════════════════════════════════════════════════════════════
def open_stego_menu(parent):
    win = _new_toplevel(parent, "Image Steganography", "840x600")
    _StegoWindow(win)


# ════════════════════════════════════════════════════════════════════════
class _StegoWindow:
    def __init__(self, win: ctk.CTkToplevel):
        self.win   = win
        self.orig_img: Optional[Image.Image] = None   # immutable original
        self.carrier: Optional[Image.Image]  = None   # may contain hidden msg
        self.carrier_path: Optional[str] = None

        # layout
        self.win.grid_columnconfigure(1, weight=1)
        self.win.grid_rowconfigure(0, weight=1)
        left  = ctk.CTkFrame(win, fg_color="#1f1f1f")
        right = ctk.CTkFrame(win, fg_color="#1f1f1f")
        left.grid(row=0, column=0, sticky="nsew")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # left: image display
        self.img_label = ctk.CTkLabel(left, text="No image loaded")
        self.img_label.place(relx=0.5, rely=0.5, anchor="center")

        # right: text box + buttons
        ctk.CTkLabel(right, text="Message").grid(row=0, column=0, pady=(10, 0))
        self.textbox = ctk.CTkTextbox(right, height=120, wrap="word")
        self.textbox.grid(row=1, column=0, padx=10, pady=6, sticky="nsew")

        btn_fr = ctk.CTkFrame(right, fg_color="#2a2a2a")
        btn_fr.grid(row=2, column=0, pady=8)
        for text, cmd in (
            ("Open Img",       self.open_image),
            ("Hide ➜ New",     self.hide_message),
            ("Reveal",         self.reveal_message),
            ("Save Carrier",   self.save_carrier),
        ):
            ctk.CTkButton(btn_fr, text=text, command=cmd, width=120).pack(side="left", padx=4)
        ctk.CTkButton(btn_fr, text="Exit", command=self.win.destroy, width=120).pack(side="left", padx=4)
    # ─────────────────── helpers ──────────────────────
    def _display_image(self, img: Image.Image):
        """Show a thumbnail preview without touching the original object."""
        preview = img.copy()
        preview.thumbnail((360, 360))
        self.img_label.configure(
            image=ctk.CTkImage(light_image=preview, size=preview.size),
            text=""
        )

    # ─────────────────── UI actions ───────────────────
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose image",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("All", "*.*")]
        )
        if not path:
            return
        try:
            # load entire file into memory so no file-handle remains open
            with Image.open(path) as img_in:
                img_in.load()                          # force data read
                img = img_in.convert("RGB")            # ensure RGB
            self.orig_img      = img
            self.carrier       = img.copy()
            self.carrier_path  = path
            self._display_image(img)
            self.textbox.delete("1.0", "end")          # clear any old text
        except Exception as e:
            messagebox.showerror("Image", f"Unable to open: {e}")

    def hide_message(self):
        if not self.orig_img:
            messagebox.showwarning("Image", "Open an image first.")
            return
        plaintext = self.textbox.get("1.0", "end").rstrip()
        if not plaintext:
            messagebox.showwarning("Text", "Nothing to hide.")
            return
        try:
            # create a *fresh* copy each time to avoid “closed image” errors
            base   = self.orig_img.copy()
            base.load()
            self.carrier = lsb.hide(base, plaintext)
            self._display_image(self.carrier)
            self.textbox.delete("1.0", "end")          # clear after hide
            messagebox.showinfo("Hide", "Message hidden in carrier.")
        except Exception as e:
            LOG.exception("hide failed")
            messagebox.showerror("Hide", f"Error: {e}")

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
        except Exception as e:
            LOG.exception("reveal failed")
            messagebox.showerror("Reveal", f"Error: {e}")

    def save_carrier(self):
        if not self.carrier:
            messagebox.showwarning("Image", "Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            title="Save image with hidden message"
        )
        if not path:
            return
        try:
            # ensure underlying pixel data is loaded before saving
            img_to_save = self.carrier.copy()
            img_to_save.load()
            img_to_save.save(path, format="PNG")
            messagebox.showinfo("Saved", f"Carrier saved to {path}")
        except Exception as e:
            LOG.exception("save failed")
            messagebox.showerror("Save", f"Unable to save: {e}")


# ════════════════════════════════════════════════════════════════════════
def _new_toplevel(parent, title, geom) -> ctk.CTkToplevel:
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry(geom)
    win.transient(parent)
    win.lift()
    win.attributes("-topmost", True)
    win.after_idle(lambda: win.attributes("-topmost", False))
    win.grab_set()
    win.focus_force()
    return win
