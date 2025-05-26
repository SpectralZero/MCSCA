# admin.py  – Secure‑Chat Admin GUI (v2.2)
import socket, ssl, sys, time
from secure_chat_server import PORT_DEFAULT
PORT_DEFAULT = PORT_DEFAULT         # keep this in one place (import from server module or keep it )
SERVER_HOST  = "127.0.0.1"   # or read from env / CLI

"""
    ADMIN gui for handling users and USB keys.
    This is a simple GUI for managing users and USB keys in the Secure-Chat application and 
    apply changes to the database. It allows the admin to add, delete, and update users,
    program USB keys, and unlock users who have been locked out due to failed USB authentication.

    -------- The SERVER must be running before this GUI can be used. --------

"""

def server_is_up(host: str = SERVER_HOST, port: int = PORT_DEFAULT, timeout=2) -> bool:
    """
    Returns True if the Secure-Chat server is listening.
    Works whether the server is wrapped in TLS or not - we only care
    about a completed TCP three-way handshake.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

# ---------- Abort early if the listener is down ----------
if not server_is_up():
    print(f"[Admin] Server is not running on {SERVER_HOST}:{PORT_DEFAULT}.  "
          f"Start secure_chat_server.py first.", file=sys.stderr)
    time.sleep(3)            # let the user read the message when double‑clicking
    sys.exit(1)
# admin.py  – Secure‑Chat Admin GUI (v2.0)
import customtkinter as ctk
import sqlite3, time, importlib, win32api, win32file
from CTkMessagebox import CTkMessagebox
from customtkinter import CTkInputDialog
from security.email_alert import get_system_info, format_email_body, send_email_alert

from security.email_otp import send_otp_email, verify_otp
from ui.otp_ui import OTPWindow 
from utils.db_setup import _verify_password, DB_PATH
from utils.usb_auth  import admin_usb_authentication as usb_authenticate
from ctk_gui.widgets.full_log_tab import FullLogTab  # Import the LogTab viewer

# ---------- CLI helpers (from manage_users.py) ----------
manage = importlib.import_module("manage_users")
add_user_cli    = manage.add
update_user_cli = manage.update
delete_user_cli = manage.delete
program_usb_cli = manage.program_usb




ctk.deactivate_automatic_dpi_awareness()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ---------- USB helper functions ----------
def list_removable_drives():
    drives = win32api.GetLogicalDriveStrings().split("\000")[:-1]
    out = []
    for d in drives:
        if win32file.GetDriveType(d) == win32file.DRIVE_REMOVABLE: # DRIVE_REMOVABLE = USBDRIVE
            try:
                label, serial, *_ = win32api.GetVolumeInformation(d) # *_ ignored other fields
                out.append((d, label or "NO_LABEL", str(serial)))   # drive path, volume label, and serial number (converted to a string) are appended as a tuple to the out list.
            except Exception:
                pass
    return out

def choose_usb_dialog():
    drives = list_removable_drives()
    if not drives:
        CTkMessagebox(title="USB", message="No removable drives found.")
        return None
    text = "\n".join(f"{i+1}. {root}  [{label}]  serial= {serial}" # i = index, root = drive path, label = volume label, serial = serial number
                     for i, (root, label, serial) in enumerate(drives))
    dlg  = CTkInputDialog(title="Select USB",
                          text=f"Plug in the stick and enter its number:\n\n{text}")
    num  = dlg.get_input()
    if not num or not num.isdigit():
        return None
    idx = int(num)
    if 1 <= idx <= len(drives):
        return drives[idx-1]          # (root,label,serial)
    return None

def serial_in_use(serial):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE usb_serial=?", (serial,))
    row = cur.fetchone(); conn.close()
    return row[0] if row else None

# ---------- Main GUI ----------
class AdminApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Secure-Chat Admin")
        self.geometry("620x470")
        # Track login attempts for password failures
        self.login_attempts = 0
        self.max_login_attempts = 3
        self._login_screen()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    def toggle_theme(self):
        ctk.set_appearance_mode("Light" if ctk.get_appearance_mode() == "Dark" else "Dark")    
        
    def _login_screen(self):
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=60, pady=60)
        u_ent = ctk.CTkEntry(frame, placeholder_text="Username")
        p_ent = ctk.CTkEntry(frame, placeholder_text="Password", show="*")

         # Theme toggle switch
        theme_toggle = ctk.CTkSwitch(self, text="Dark Mode", command=self.toggle_theme)
        theme_toggle.place(x=10, y=10)

        u_ent.pack(pady=8); p_ent.pack(pady=8)

        def try_login():
            username = u_ent.get().strip(); pwd = p_ent.get().strip()
            conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
            cur.execute("SELECT password, role FROM users WHERE username=?", (username,))
            row = cur.fetchone(); conn.close()

            if not (row and row[1] == "admin" and _verify_password(row[0], pwd)):
                # 2) Wrong creds → increment and maybe OTP
                self.login_attempts += 1
                if self.login_attempts < self.max_login_attempts:
                    CTkMessagebox(
                        title="Login failed",
                        message=f"Wrong credentials ({self.login_attempts}/{self.max_login_attempts})."
                    )
                    return
                # on the 3rd wrong attempt → OTP fallback
                otp = OTPWindow(self)
                otp.grab_set()
                otp.wait_window()
                if not getattr(otp, 'verified', False):
                    CTkMessagebox(title="OTP Error", message="Invalid or expired OTP.")
                    return
                # OTP succeeded → now treat as “logged in” and move on to USB

            # 3) USB 2FA (up to 3 attempts)
            for attempt in range(3):
                if usb_authenticate(username):
                    # USB ok → dashboard
                    frame.destroy()
                    self._dashboard()
                    return

                if attempt < 2:
                    CTkMessagebox(
                        title="USB",
                        message=f"Wrong USB ({attempt+1}/3). Try again."
                    )
                else:
                    # 3rd USB failure → OTP fallback
                    otp = OTPWindow(self)
                    otp.grab_set()
                    otp.wait_window()
                    if getattr(otp, 'verified', False):
                        frame.destroy()
                        self._dashboard()
                        return
                    CTkMessagebox(title="OTP Error", message="Invalid or expired OTP.")
                    return

        ctk.CTkButton(frame, text="Login", command=try_login).pack(pady=15)

    # ----- DASHBOARD -----
    def _dashboard(self):
        left  = ctk.CTkFrame(self, width=220); left.pack(side="left", fill="y", padx=5, pady=5)
        right = ctk.CTkFrame(self);            right.pack(side="right", expand=True, fill="both", padx=5, pady=5)


        
        self.user_list = ctk.CTkTextbox(left, width=200)
        self.user_list.pack(fill="both", expand=True, padx=4, pady=4)
        self._refresh_users()

        self.info = ctk.CTkLabel(right, text="Select an action", anchor="w", justify="left")
        self.info.pack(anchor="nw", pady=(12,0), padx=10)

        btn = lambda txt, cmd: ctk.CTkButton(right, text=txt, width=190,
                                             corner_radius=8, command=cmd).pack(padx=8, pady=6)
        btn("Add user",              self._add)
        btn("Delete user",           self._delete)
        btn("Change password",       self._passwd)
        btn("Program / Re-key USB",  self._rekey)
        btn("View Locked Users",     self._view_locked)
        btn("Unlock User",           self._unlock)
        btn("View Logs",             self.view_logs)  # New button for logs
        btn ("Exit", self._on_close)

    # ----- helpers -----
    def _refresh_users(self):  # updating a user interface element with a list of usernames retrieved from a database. 
        self.user_list.configure(state="normal"); self.user_list.delete("1.0","end")
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        for (u,) in cur.execute("SELECT username FROM users ORDER BY username"):
            self.user_list.insert("end", u + "\n")
        conn.close(); self.user_list.configure(state="disabled")

    def _prompt(self, title, text):
        dlg = CTkInputDialog(title=title, text=text); val = dlg.get_input()
        return val.strip() if val else None

    def _set_info(self, msg): self.info.configure(text=msg)

    # ----- callbacks -----
    def _add(self):
        u = self._prompt("Add user","Username")
        p = self._prompt("Add user","Password")
        sel = choose_usb_dialog()
        if u and p and sel:
            try:
                program_root, *_ = sel
                add_user_cli(u, p, program_root)
                self._refresh_users(); self._set_info(f"User '{u}' added.")
            except SystemExit as e:
                CTkMessagebox(title="Error", message=str(e))

    def _delete(self):
        u = self._prompt("Delete user","Username")
        if u:
            delete_user_cli(u); self._refresh_users(); self._set_info(f"User '{u}' deleted.")

    def _passwd(self):
        u = self._prompt("Change password","Username")
        p = self._prompt("Change password","New password")
        if u and p:
            update_user_cli(u, p, None); self._set_info(f"Password for '{u}' updated.")

    def _rekey(self):
        u = self._prompt("Program USB","Username")
        if not u: return
        sel = choose_usb_dialog()
        if not sel: return
        root,label,serial = sel

        # serial already assigned to someone else?
        used = serial_in_use(serial)
        if used and used != u:
            CTkMessagebox(title="USB in use", message=f"Stick already assigned to '{used}'."); return

        # user exists?
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT usb_serial FROM users WHERE username=?", (u,)); row = cur.fetchone(); conn.close()
        if not row:
            CTkMessagebox(title="Error", message="User not found."); return
        if row[0] and row[0] != serial:
            ans = CTkMessagebox(title="Replace key?",
                                message=f"'{u}' already has a key.\nReplace it?",
                                option_1="Yes", option_2="Cancel").get()
            if ans != "Yes": return
        try:
            program_usb_cli(u, root)
            self._set_info(f"USB ({root}) programmed for '{u}'.")
        except SystemExit as e:
            CTkMessagebox(title="Error", message=str(e))

    # -- view / unlock locks --
    def _view_locked(self):
        now = int(time.time())
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT username, usb_locked_until FROM users WHERE usb_locked_until > ?", (now,))
        rows = cur.fetchall(); conn.close()
        if not rows:
            CTkMessagebox(title="Locked Users", message="No locked accounts."); return
        lines = [f"{u} locked for {((t-now)//60)}m {((t-now)%60)}s" for u,t in rows]
        CTkMessagebox(title="Locked Users", message="\n".join(lines))

    def _unlock(self):
        u = self._prompt("Unlock user","Username to unlock")
        if not u: return
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("UPDATE users SET usb_locked_until=0, usb_fail_count=0 WHERE username=?", (u,))
        ok = cur.rowcount; conn.commit(); conn.close()
        if ok:
            CTkMessagebox(title="Unlocked", message=f"User '{u}' unlocked.")
        else:
            CTkMessagebox(title="Error", message=f"User '{u}' not found or not locked.")

    def view_logs(self):
        """Open the full-file log viewer in a new window."""
        win = ctk.CTkToplevel(self)
        win.title("Secure-Chat Logs")
        win.geometry("800x600")

        # Make it pop above the admin window:
        win.transient(self)         # treat as child of AdminApp
        win.lift()                  # raise above all siblings
        win.focus_force()           # grab keyboard focus
        # optional: win.attributes("-topmost", True)  # for guaranteed-on-top

        full_tab = FullLogTab(win)
        full_tab.pack(expand=True, fill="both")        

    def _on_close(self):
        # If you ever need to do cleanup, do it here…
        self.destroy()
        sys.exit(0)
# ---------- run ----------
if __name__ == "__main__":
    AdminApp().mainloop()
