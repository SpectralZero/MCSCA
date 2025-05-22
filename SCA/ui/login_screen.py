# ui/login_screen.py
import customtkinter as ctk
import tkinter
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class LoginDialog(ctk.CTkToplevel):
    """
    Modal username / password prompt.

    • Returns (username, password) via self.result
      - None if the user cancels or fails 3x.
    """

    def __init__(self, parent, max_attempts: int = 3):
        super().__init__(parent)
        self.title("Sign in")
        self.geometry("500x600")
        self.resizable(False, False)
        self.result = None
        self._attempts_left = max_attempts

        # make this window modal
        self.transient(parent)
        self.grab_set()

        # ---------- UI ----------
        self.frame = ctk.CTkFrame(
            master=self,
             width=320,
            height=360,
            corner_radius=15
        )
        self.frame.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)    

        # Title label
        self.login_label = ctk.CTkLabel(
            master=self.frame,
            text="Log in",
            font=('Century Gothic', 30)
        )
        self.login_label.place(x=100, y=45)

        # Username entry
        self.username_entry = ctk.CTkEntry(
            master=self.frame,
            width=220,
            placeholder_text='Username'
        )
        self.username_entry.place(x=50, y=110)

        # Password entry
        self.password_entry = ctk.CTkEntry(
            master=self.frame,
            width=220,
            placeholder_text='Password',
            show="*"
        )
        self.password_entry.place(x=50, y=165)

        # Status label (needed for login_failed)
        self.status_lbl = ctk.CTkLabel(
            master=self.frame,
            text="",
            text_color="#ff4444",
            font=("Arial", 12)
        )

        # Login button
        login_button = ctk.CTkButton(
            master=self.frame,
            width=220,
            text="Login",
            corner_radius=6,
            command=self._on_login
        )
        login_button.place(x=50, y=250)

        # Bind Enter key to login
        self.bind("<Return>", self._on_login)

    # ---------- callbacks ----------
    def _on_login(self, _event=None):
        user = self.username_entry.get().strip()
        pwd = self.password_entry.get().strip()

        if not user or not pwd:
            messagebox.showerror("Error", "Username and password required.", parent=self)
            return

        # Success → return creds to caller
        self.result = (user, pwd)
        self.destroy()

    def login_failed(self):
        """
        Call this from the parent if the server replies 'FAIL'.
        Shows error & decrements attempts; destroys window on 3rd fail.
        """
        self._attempts_left -= 1
        if self._attempts_left <= 0:
            messagebox.showerror("Access denied", "Too many attempts.")
            self.destroy()
            return
        self.status_lbl.configure(
            text=f"Invalid credentials. Attempts left: {self._attempts_left}", text_color="#ff4444"
        )
        self.password_entry.delete(0, tkinter.END)
