"""
Theme helpers for the CustomTkinter GUI.

Public API
----------
apply_theme("dark" | "light")
toggle_theme()  -> returns the new mode
"""

from __future__ import annotations

from typing import Literal

import customtkinter as ctk

# We’ll sync the global flag inside style_utils
from ctk_gui.ui_theme.utils import style_utils
import cairosvg
from PIL import Image
import io
from pathlib import Path
from io import BytesIO
from PIL import Image
import customtkinter as ctk
ASSETS = Path(__file__).resolve().parent / "assets"
# Optional: SVG → PNG conversion needs cairosvg; pillow alone handles PNG/JPG
try:
    import cairosvg
    _SVG = True
except ImportError:
    _SVG = False     # will warn and fall back if you haven’t pip‑installed cairosvg

import tkinter as _tk

# ensure there is a default root for CTkFont to attach to
if not _tk._default_root:
    __hidden_root = _tk.Tk()
    __hidden_root.withdraw()

FONT_BODY = ctk.CTkFont(size=16, weight="normal")
def load_icon(filename: str, size: tuple[int,int]) -> ctk.CTkImage:
    svg_path = ASSETS / filename
    png_bytes = cairosvg.svg2png(url=str(svg_path),
                                 output_width=size[0],
                                 output_height=size[1])
    pil = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=size)

# ─────────────────────────── public API ────────────────────────────
def apply_theme(mode: Literal["light", "dark"]) -> None:
    """Instantly switch to *light* or *dark*."""
    mode = mode.lower()
    if mode not in {"light", "dark"}:
        raise ValueError(f"Unknown appearance mode: {mode!r}")

    ctk.set_appearance_mode(mode.capitalize())
    style_utils.APP_THEME = mode  # <<< keep helpers in sync


def toggle_theme() -> str:
    """
    Toggle between dark and light modes.

    Returns
    -------
    str
        The new mode (“dark” or “light”).
    """
    current = ctk.get_appearance_mode().lower()
    new_mode = "dark" if current == "light" else "light"
    apply_theme(new_mode)
    return new_mode
