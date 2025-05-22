import os
import customtkinter as ctk
from customtkinter import CTkImage, CTkToplevel
from security.email_otp import send_otp_email, verify_otp
from security.email_alert import get_system_info, format_email_body, send_email_alert

from PIL import Image

# Customize appearance
ctk.set_appearance_mode("System")       # "System", "Dark", "Light"
ctk.set_default_color_theme("dark-blue")  # themes: "blue", "green", "dark-blue"

# Fixed admin OTP email
ADMIN_OTP_EMAIL = "jzororonoro@gmail.com"

class OTPWindow(CTkToplevel):
    RESEND_COOLDOWN = 30             # seconds to wait between resends
    MAX_VERIFY_ATTEMPTS = 3          # max wrong OTP entries
    def __init__(self, parent=None, validity_seconds=60):
        # Initialize as a true toplevel of the admin window
        if hasattr(parent, 'tk'):
            super().__init__(parent)
            self.parent = parent
        else:
            super().__init__()
            self.parent = None

        self.email = ADMIN_OTP_EMAIL
        self.verified = False
        self.verify_attempts = 0
        self.resend_count = 0
        self.max_resends = 5
        self.validity = validity_seconds
        self.remaining = validity_seconds
        self._after_id = None

        # Window setup
        self.title("🔐 Admin OTP Verification")
        self.geometry("650x350")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.grid_columnconfigure(0, weight=1)

        # Load email icon via CTkImage for DPI scaling
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_file = os.path.join(script_dir, "email.png")
        try:
            pil_img = Image.open(icon_file).resize((40, 40))
            ctki = CTkImage(light_image=pil_img, size=(40, 40))
        except Exception:
            ctki = None

        # Header frame
        header = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color="#1f1f2e",
            border_width=2,
            border_color="#44475a"
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        header.grid_columnconfigure(1, weight=1)

        if ctki:
            ctk.CTkLabel(header, image=ctki, text="", fg_color="transparent").grid(row=0, column=0, padx=10)
            self.icon_ref = ctki

        ctk.CTkLabel(
            header,
            text=f"Enter the OTP Admin ",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        ).grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Progress bar & timer label
        self.progress = ctk.CTkProgressBar(self, width=340)
        self.progress.grid(row=1, column=0, pady=(5, 0))
        self.time_label = ctk.CTkLabel(self, text="05:00", font=ctk.CTkFont(size=14))
        self.time_label.grid(row=2, column=0, pady=(0, 15))

        # Entry frame for OTP
        entry_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#2a2a3d")
        entry_frame.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="------",
            justify="center",
            width=280,
            font=ctk.CTkFont(size=18)
        )
        self.entry.grid(row=0, column=0, pady=15)

        # Buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=10)

        self.verify_btn = ctk.CTkButton(btn_frame, text="Verify", command=self.check, width=120)
        self.verify_btn.grid(row=0, column=0, padx=(0, 10))
        self.resend_btn = ctk.CTkButton(btn_frame, text="Resend OTP", command=self.resend, width=120)
        self.resend_btn.grid(row=0, column=1)

        # Status message label
        self.status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color="#ff6b6b")
        self.status.grid(row=5, column=0, pady=(5, 10))

       
        # Send initial OTP and start countdown
        send_otp_email(self.email)
        self._after_id = self.after(1000, self.update_timer)

    def update_timer(self):
        if self.remaining > 0:
            self.remaining -= 1
            mins, secs = divmod(self.remaining, 60)
            self.time_label.configure(text=f"{mins:02d}:{secs:02d}")
            self.progress.set((self.validity - self.remaining) / self.validity)
            self._after_id = self.after(1000, self.update_timer)
        else:
            self.status.configure(text="⏰ OTP expired. Click 'Resend OTP'.")
            self.verify_btn.configure(state="disabled")

    def check(self):
        code = self.entry.get().strip()
        if verify_otp(self.email, code):
            if self._after_id:
                self.after_cancel(self._after_id)
            self.verified = True
            self.destroy()
            if self.parent:
                self.parent.focus()
        else:
            self.verify_attempts += 1  # ── INCREMENT ATTEMPTS ──
            if self.verify_attempts >= self.MAX_VERIFY_ATTEMPTS:
                self.status.configure(text=f"❌ Too many failed attempts ({self.MAX_VERIFY_ATTEMPTS}).")
                self.verify_btn.configure(state="disabled")
                self.destroy()
                # Send an email alert about the failed authentication attempts
                system_info = get_system_info()
                subject = "USB Authentication Failed"
                email_body, logo_data, icon_data = format_email_body(system_info,OTPWindow.MAX_VERIFY_ATTEMPTS)
                to_email = "jzororonoro@gmail.com"
                send_email_alert(subject, email_body, to_email, logo_data)
                return
                # optionally: self.destroy()
            else:
                remaining = self.MAX_VERIFY_ATTEMPTS - self.verify_attempts
                self.status.configure(text=f"❌ Invalid OTP. {remaining} tries left.")
                

    def resend(self):
        # ── DISABLE BUTTON & START COOL-DOWN ──
        self.resend_btn.configure(state="disabled")
        send_otp_email(self.email)
        self.remaining = self.validity
        self.verify_btn.configure(state="normal")
        self.status.configure(text="🔄 OTP resent. Check your inbox.")
        # if you want to count total resends:
        self.resend_count += 1
        if self.resend_count >= self.max_resends:
            self.resend_btn.configure(state="disabled")

        # start resend cooldown timer
        self._resend_cooldown = self.RESEND_COOLDOWN
        self._update_resend_timer()
        # reset countdown for OTP validity
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(1000, self.update_timer)

    def _update_resend_timer(self):
        if self._resend_cooldown > 0:
            # optional: show seconds left on the button
            self.resend_btn.configure(text=f"Resend ({self._resend_cooldown}s)")
            self._resend_cooldown -= 1
            self.after(1000, self._update_resend_timer)
        else:
            self.resend_btn.configure(text="Resend OTP", state="normal")

    def toggle_theme(self):
        ctk.set_appearance_mode("Light" if ctk.get_appearance_mode() == "Dark" else "Dark")

    def on_close(self):
        # Cancel pending callbacks
        if self._after_id:
            self.after_cancel(self._after_id)
        self.verified = False
        self.destroy()
        if self.parent:
            self.parent.focus()