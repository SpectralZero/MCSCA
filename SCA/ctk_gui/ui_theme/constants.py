from pathlib import Path

# ─── figure out where this file lives ───────────────────────────────
HERE   = Path(__file__).resolve().parent       # .../ss/ctk_gui/ui_theme
PKG    = HERE.parent                           # .../ss/ctk_gui
ASSETS = PKG / "assets"                        # .../ss/ctk_gui/assets

# ─── background image paths ──────────────────────────────────────────
BG_DARK  = ASSETS / "bg_dark.jpg"
BG_LIGHT = ASSETS / "bg_light.jpg"