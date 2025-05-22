# ctk_gui/ui_theme/window_utils.py
def center_window(window, width: int, height: int):
    window.geometry(f"{width}x{height}")
    window.update_idletasks()
    sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")
