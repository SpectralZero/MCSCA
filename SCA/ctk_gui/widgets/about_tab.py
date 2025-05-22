# ctk_gui/widgets/about_tab.py

from __future__ import annotations
import customtkinter as ctk


class AboutTab(ctk.CTkFrame):
    """
    Displays project details, version info, authorship, and technology stack.
    """

    def __init__(self, master, **kw):
        super().__init__(master, **kw)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Container card (glass-like transparency)
        card = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        card.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        about_text = """
SecureChatApp - Secure Chat Launcher
───────────────────────────────────────
Version: 1.0.0
Release Year: 2025

Authors:
 • Jamal Alqbail
 • Ahmad Albwab
 • Mubarak Nabeeh

Supervised by: Dr. Salah ALghyaleen 

Overview:
SecureChatApp is a multi-layered secure communication platform designed for high-trust environments. 
It is developed as a final-year university project focused on privacy, encryption, and user security.

Core Technologies:
 • Python 3.12
 • CustomTkinter GUI Framework
 • TLS 1.3 Encryption (SSL Context)
 • ECDH + AES-256-GCM Secure Messaging
 • SQLite3 (User & Chat Logs DB)
 • USB-Based Two-Factor Authentication
 • Image LSB Steganography
 • Secure File Transfer & Shredding
 • Dark/Light Theme Switcher
 

Features:
 • Start/stop secure server with live logging
 • Connect multiple clients with TLS handshake
 • Broadcast & Private Messaging support
 • Real-time encrypted chat logs
 • Modular navigation tabs:
     - Server
     - Clients
     - Database
     - Logs
     - Security Tools
     - About

Project Use Case:
Designed for environments requiring complete message confidentiality, such as secure enterprise 
communications, whistleblower platforms, and personal encrypted chat.

Legal Notice:
This software is a proof-of-concept academic project.
© 2025 Jamal Alqbail. All rights reserved.

        """.strip()

        textbox = ctk.CTkTextbox(card, wrap="word", font=("Bahnschrift SemiLight SemiConde", 18), state="normal")
        textbox.insert("0.0", about_text)
        textbox.configure(state="disabled", fg_color=card.cget("fg_color"))
        textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
