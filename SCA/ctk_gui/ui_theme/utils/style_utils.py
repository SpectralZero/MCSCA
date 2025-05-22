import customtkinter as ctk
from ctk_gui.ui_theme.utils.constants import BG_DARK, BG_WHITE

APP_THEME = "dark"
BG_IMAGE_PATH = BG_DARK

def apply_theme():
    ctk.set_appearance_mode(APP_THEME)
    ctk.set_default_color_theme("blue")

def toggle_theme():
    global APP_THEME
    if APP_THEME == "dark":
        APP_THEME= "light"
    else:
        APP_THEME = "dark"
    apply_theme()

def get_theme_colors():
    if APP_THEME == "dark":
        return {"fg": "#212121", "hover": "#2a2d2e", "text": "white"}
    else:
        return {"fg": "#f5f5f5", "hover": "#e0e0e0", "text": "black"}

def get_bg_image_path():
    return str(BG_IMAGE_PATH)

def set_card_background(widget: ctk.CTkFrame) -> None:
    """
    Style a “card” (CTkFrame) to match the current theme.
    Uses the same fg_color as other UI elements.
    """
    colors = get_theme_colors()
    widget.configure(fg_color=colors["fg"])
