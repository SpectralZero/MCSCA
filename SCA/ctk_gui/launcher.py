# ctk_gui/launcher.py
from __future__ import annotations
import logging
from pathlib import Path
import os
import customtkinter as ctk

import tkinter as tk
from ctk_gui.ui_theme.utils.style_utils import (
    apply_theme,
    toggle_theme,
    get_theme_colors,
   
)

from ctk_gui.ui_theme.utils.window_utils import center_window

from ctk_gui.widgets.server_tab import ServerTab

log = logging.getLogger(__name__)

class AppWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        logging.basicConfig(level=logging.INFO)

        # ─── Theme & Window setup ─────────────────────────────────────
        apply_theme()
        self.title("SecureChatApp Launcher")
        self.width, self.height = 1350, 740
        self.minsize(900, 540)
        center_window(self, self.width, self.height)

        self.protocol("WM_DELETE_WINDOW", self._on_exit)

        colors = get_theme_colors()
        # allow content area to expand
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # # ─── Background image ─────────────────────────────────────────
        # bg_path = Path(get_bg_image_path())
        # pil_img = Image.open(bg_path).resize((self.width, self.height))
        # self._bg_photo = ImageTk.PhotoImage(pil_img)
        # # use a standard tkinter.Label for background to avoid CTkImage scaling issues
        # tk.Label(self, image=self._bg_photo, bd=0).place(
        #     x=0, y=0, relwidth=1, relheight=1
        # )

        # ─── Sidebar ───────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, corner_radius=0, width=250, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="ns")

        # theme switch
        self.switch = ctk.CTkSwitch(
            master=self.sidebar,
            text="Dark Mode",
            command=self._on_toggle_theme
        )
        self.switch.pack(pady=20, padx=20)
        if ctk.get_appearance_mode().lower() == "dark":
            self.switch.select()
        else:
            self.switch.deselect()

        # nav buttons
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        for label in ("Server", "Clients", "Database","Logs", "DEMO", "About", "Exit"):
            
            if label == "Exit":
                cmd = self._on_exit
            elif label == "DEMO":
                cmd = self._show_demo
            else:
                cmd = lambda l=label: self._show_page(l)
            btn = ctk.CTkButton(
                master=self.sidebar,
                text=label,
                width=210, height=89,
                anchor="center",
                fg_color=colors['fg'],
                hover_color=colors['hover'],
                text_color=colors['text'],
                font=("Cascadia Code", 18, "bold"),
                    command=cmd
)
                
            
            self._nav_buttons[label] = btn
            btn.pack(pady=3, padx=3, anchor="center")

        self._refresh_nav_colors()

        # ─── Content container ─────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # ─── Instantiate pages ─────────────────────────────────────────
        self.pages: dict[str, ctk.CTkFrame] = {}
        # Server tab
        self.pages["Server"] = ServerTab(self.content, fg_color="transparent")
        self.pages["Server"].grid(row=0, column=0, sticky="nsew")

        # TODO: register other pages when ready
        from ctk_gui.widgets.client_tab import ClientTab
        self.pages["Clients"] = ClientTab(self.content, fg_color="transparent")
        self.pages["Clients"].grid(row=0, column=0, sticky="nsew")

        from ctk_gui.widgets.log_tab import LogTab
        self.pages["Logs"] = LogTab(self.content, fg_color="transparent")
        self.pages["Logs"].grid(row=0, column=0, sticky="nsew")

        from ctk_gui.widgets.db_tab import DbTab
        self.pages["Database"] = DbTab(self.content, fg_color="transparent")
        self.pages["Database"].grid(row=0, column=0, sticky="nsew")

        
        

        from ctk_gui.widgets.about_tab import AboutTab
        self.pages["About"] = AboutTab(self.content, fg_color="transparent")
        self.pages["About"].grid(row=0, column=0, sticky="nsew")
        
        from ctk_gui.widgets.demo_tab import DemoTab 
        self.pages["DEMO"]     = DemoTab(self.content, fg_color="transparent"); 
        self.pages["DEMO"].grid(row=0, column=0, sticky="nsew")

        self.current_page = "Server"
        

        self._show_page(self.current_page)
        # hide all except initial
        for name, page in self.pages.items():
            if name != self.current_page:
                page.grid_remove()

    def _show_demo(self):
        self._show_page("DEMO")
        # trigger the embedded player
        self.pages["DEMO"].load_and_play()
        

        

    def _show_page(self, name: str) -> None:
        if name not in self.pages:
            log.warning("No page registered for %r", name)
            return

        self.pages[self.current_page].grid_remove()
        self.pages[name].grid()
        self.current_page = name
        

    def _on_toggle_theme(self) -> None:
        toggle_theme()
        new = ctk.get_appearance_mode().capitalize()
        self.switch.configure(text=f"{new} Mode")
        self._refresh_nav_colors()

        for page in self.pages.values():
            # only pages that implement update_theme will be called
            if hasattr(page, "update_theme"):
                page.update_theme()

    def _refresh_nav_colors(self) -> None:
        colors = get_theme_colors()
        for btn in self._nav_buttons.values():
            btn.configure(
                fg_color=colors["fg"],
                hover_color=colors["hover"],
                text_color=colors["text"],
            )
            
    def _cancel_all_after_jobs(self, widget: tk.Misc) -> None:
        """
        Cancel any scheduled `after()` jobs on `widget`, 
        looking for attributes starting with '_after' or containing 'job'.
        """
        for attr in dir(widget):
            if attr.startswith("_after") or "job" in attr.lower():
                job = getattr(widget, attr, None)
                try:
                    widget.after_cancel(job)
                except Exception:
                    pass


    def _on_exit(self) -> None:
        # 1) Cancel your own scheduled jobs
        self._cancel_all_after_jobs(self)
        for page in self.pages.values():
            self._cancel_all_after_jobs(page)

        # 2) Tear down the GUI
        self.quit()
        self.destroy()

        # 3) Immediately kill the process so no CTk threads linger
        os._exit(0)


                      
if __name__ == "__main__":
    AppWindow().mainloop()