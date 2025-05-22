from __future__ import annotations
import customtkinter as ctk
from ctk_gui.theme import load_icon

class SideButton(ctk.CTkButton):
    """
    Small square icon button for sidebar / top-bar (40 × 40 px).
    Uses CTkImage from load_icon for proper scaling on High-DPI displays.
    """

    def __init__(self, master, svg_filename: str, tooltip_text: str, command=None):
        # Load the icon as a CTkImage
        icon_ctk_img = load_icon(svg_filename, size=(20, 20))
        # Keep CTkImage reference
        self._icon_ctk_img = icon_ctk_img

        super().__init__(
            master,
            image=self._icon_ctk_img,
            text="",
            width=40,
            height=40,
            fg_color="transparent",
            hover=False,
            corner_radius=0,
            command=command,
        )
        self.configure(cursor="hand2")

        # Immediately store the scaled PhotoImage to prevent GC
        try:
            scale = self._get_widget_scaling()
            photo = self._icon_ctk_img.create_scaled_photo_image(scale)
            self._image_label.configure(image=photo)
            # keep reference so it isn't garbage-collected
            self._photo_image = photo
        except Exception:
            pass

        self._create_tooltip(tooltip_text)

    def _create_tooltip(self, text: str) -> None:
        if not text:
            return

        tip = ctk.CTkLabel(
            master=self,
            text=text,
            fg_color=("#333", "#333"),
            text_color="#fff",
            font=ctk.CTkFont(size=10),
            corner_radius=4,
            padx=4,
            pady=2,
        )
        tip.place_forget()

        def enter(_):
            x, y = self.winfo_pointerxy()
            tip.place(x=x + 14, y=y + 14, anchor="nw")

        def leave(_):
            tip.place_forget()

        self.bind("<Enter>", enter, add="+")
        self.bind("<Leave>", leave, add="+")