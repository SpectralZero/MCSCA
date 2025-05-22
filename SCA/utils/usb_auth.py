# usb_auth.py
import os, time, hashlib, logging, win32api, win32file, sqlite3
from tkinter import messagebox
from utils.db_setup import DB_PATH


MAX_FAILS = 3
LOCK_SECS = 120

def _drive_serial(drive_root: str) -> str | None:  # list =[1,2,3 ]   print(list[0]) 
    try:
        return str(win32api.GetVolumeInformation(drive_root)[1]) # volume name, serial number, maximum file name length, file system flags, and file system name.
    except Exception:
        return None

def _find_key_file(serial: str) -> str | None:
    for d in win32api.GetLogicalDriveStrings().split('\000')[:-1]:# "C:\\\000D:\\\000E:\\\000"
        if _drive_serial(d) == serial:
            kp = os.path.join(d, "key.dat")
            return kp if os.path.exists(kp) else None
    return None

def authenticate(username: str) -> bool:
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT usb_serial, usb_hash, usb_fail_count, usb_locked_until FROM users WHERE username=?", (username,))
    row = cur.fetchone(); conn.close()
    if not row or not row[0]:
        messagebox.showerror("USB", "No USB key registered for this user."); return False

    serial, expect_hash, fails, locked_until = row
    now = int(time.time())
    if locked_until and locked_until > now:
        mins = (locked_until - now)//60
        messagebox.showwarning("USB", f"Locked out. Try again in {mins} min."); return False

    key_path = _find_key_file(serial)
    if not key_path:
        return _fail(username, fails, "Correct USB key not inserted.")

    actual = hashlib.sha256(open(key_path, "rb").read()).hexdigest() # hexdigest() returns a string object of double length, containing only hexadecimal digits.
    if actual != expect_hash:
        return _fail(username, fails, "USB key authentication failed.")

    # success
    _reset_fails(username)
    return True

def admin_usb_authentication(username: str) -> bool:
    """Bypass fail counts and locking for admin checks."""
    # Fetch serial and expected hash
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT usb_serial, usb_hash FROM users WHERE username=?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        messagebox.showerror("USB", "No USB key registered for this user.")
        return False

    serial, expect_hash = row
    key_path = _find_key_file(serial)
    if not key_path:
        messagebox.showerror("USB", "Correct USB key not inserted.")
        return False

    with open(key_path, 'rb') as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    if actual_hash != expect_hash:
        messagebox.showerror("USB", "USB key authentication failed.")
        return False

    # Admin check succeeded
    return True
    
def _fail(user, fails, msg):
    messagebox.showerror("USB", msg)
    fails += 1
    lock = int(time.time()) + LOCK_SECS if fails >= MAX_FAILS else 0
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("UPDATE users SET usb_fail_count=?, usb_locked_until=? WHERE username=?", (fails % MAX_FAILS, lock, user))
    conn.commit(); conn.close()
    return False

def _reset_fails(user):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("UPDATE users SET usb_fail_count=0, usb_locked_until=0 WHERE username=?", (user,))
    conn.commit(); conn.close()

def is_locked_out(username: str) -> bool:
    """Check if user is currently locked out for USB attempts."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT usb_locked_until FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    locked_until = row[0] or 0
    return locked_until > time.time()


def authenticate_and_get_token(username: str) -> tuple[str,str] | None:
    """
    Performs the existing USB checks client-side.
    Returns (serial, sha256) on success, else None.
    """
    if authenticate(username):          # your current routine
        # -> reuse the last successful result:
        for d in win32api.GetLogicalDriveStrings().split('\000')[:-1]:
            if _drive_serial(d):
                kp = os.path.join(d, "key.dat")
                if os.path.exists(kp):
                    serial = _drive_serial(d)
                    h = hashlib.sha256(open(kp,'rb').read()).hexdigest()
                    return serial, h
    return None






"""

┌──── client ────────────────────────────────────┐           ┌───── server ─────┐
│ 1. ➜  username:password                       │    ────►  │ verify_credentials()     │
│                                                │           │ if OK → send "USBREQ"    │
│ 2. ◀── "USBREQ"                               │  ◄──────  │                           │
│ 3. ➜  usb_serial:usb_hash (TLS-protected)     │   ────►   │ verify_usb()              │
│                                                │           │  • checks serial/hash     │
│                                                │           │  • updates fail counters  │
│ 4. ◀── "SUCCESS"  /  "USBFAIL <secs>"          │  ◄────── │ or "LOCKED"                │
└─────────────────────────────────────────────────┘          └────────────────────────────┘



"""