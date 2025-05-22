"""
Base helpers reused by several widgets.
"""

import customtkinter as ctk


class CTkIconButton(ctk.CTkButton):
    """
    A transparent square button that shows only an icon.
    """

    def __init__(self, master, image, tooltip: str = "", command=None):
        super().__init__(
            master,
            image=image,
            text="",
            width=40,
            height=40,
            fg_color="transparent",
            hover=False,
            corner_radius=0,
            command=command,
        )
        self.configure(cursor="hand2")
        if tooltip:
            self._add_tooltip(tooltip)

    # ── rudimentary tooltip -------------------------------------------------
    def _add_tooltip(self, text: str):
        tip = ctk.CTkLabel(
            text=text,
            fg_color="#333",
            text_color="#fff",
            font=("Segoe UI", 10),
            corner_radius=4,
            padx=4, pady=2,
        )
        tip.withdraw()

        def enter(_):
            x, y = self.winfo_pointerxy()
            tip.place(x=x + 14, y=y + 14, anchor="nw")
            tip.deiconify()

        def leave(_):
            tip.withdraw()

        self.bind("<Enter>", enter, add="+")
        self.bind("<Leave>", leave, add="+")
