import customtkinter as ctk
from ctk_gui.theme import FONT_BODY, load_icon


class ChatPane(ctk.CTkFrame):
    """
    Scrollable history + entry box. Backend must expose .broadcast(msg).
    """

    def __init__(self, master, *, backend, **kw):
        super().__init__(master, **kw)
        self.backend = backend

        self.history = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.history.pack(fill="both", expand=True, padx=4, pady=(4, 2))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=(0, 4))

        self.msg = ctk.StringVar()
        entry = ctk.CTkEntry(row, textvariable=self.msg, font=FONT_BODY)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        entry.bind("<Return>", self._send)

        ctk.CTkButton(row, image=load_icon("send.svg"), text="", width=40, command=self._send
                      ).pack(side="right")

    def _send(self, *_):
        txt = self.msg.get().strip()
        if txt:
            self.backend.broadcast(txt)
            self.msg.set("")
            self.append(f"You: {txt}")

    def append(self, line: str):
        self.history.configure(state="normal")
        self.history.insert("end", line + "\n")
        self.history.configure(state="disabled")
        self.history.see("end")
