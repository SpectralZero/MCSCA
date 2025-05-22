#utils/db_setup.py
"""
utils/db_setup.py
=================
SQLite-based user store for the Secure Chat App.

• Automatically creates users.db on first run.
• Stores salted / PBKDF2-HMAC-SHA-256 password hashes.
• Provides `verify_credentials()` for the server.
"""
import sqlite3
import os
import hashlib
import hmac
import secrets
from pathlib import Path

# ---------- Configuration ----------
_DB_DIR   = Path(__file__).resolve().parent      # utils/
DB_PATH   = _DB_DIR / "users.db"
_ROUNDS   = 100_000                              # PBKDF2 iterations
_SALT_LEN = 16                                   # bytes
# -----------------------------------

# ---------- Internal helpers ----------
def _hash_password(password: str, salt: bytes | None = None) -> bytes:                  #salt: bytes | None → salt must be either bytes or None
    """Return salt+hash (concatenated) for storage."""
    salt = salt or secrets.token_bytes(_SALT_LEN)                                       # = None → If no salt is passed, use None by default
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ROUNDS)          #if salt is None, it creates one: secrets.token_bytes(...)

    return salt + pwd_hash                                                              #If salt is already given, it uses that


def _verify_password(stored: bytes, provided: str) -> bool:
    salt, stored_hash = stored[:_SALT_LEN], stored[_SALT_LEN:]
    new_hash = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt, _ROUNDS)
    return hmac.compare_digest(stored_hash, new_hash)
# --------------------------------------


def init_user_db() -> None:
    """
    Create `users.db` and insert the three default users the first time
    the server starts.
    """
    first_time = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS users (
               id       INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT    UNIQUE NOT NULL,
               password BLOB    NOT NULL
           )"""
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT    UNIQUE NOT NULL,
        password BLOB    NOT NULL,
        role     TEXT    NOT NULL DEFAULT 'user',
        usb_serial       TEXT,
        usb_hash         TEXT,
        usb_fail_count   INTEGER DEFAULT 0,
        usb_locked_until INTEGER DEFAULT 0
    )
""")

    if first_time:
        # Default passwords are `<username>123` – change them as you like
        initial_users = ["jamal", "ahmad", "mubarak"]
        cur.executemany(
            "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
            [(u, _hash_password(f"{u}123")) for u in initial_users],
        )
        conn.commit()

    conn.close()


def verify_credentials(username: str, password: str) -> bool:
    """Return True if username/password are correct."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return bool(row) and _verify_password(row[0], password) #_verify_password(row[0], password)  //  user exists and the password hash matches → returns True
