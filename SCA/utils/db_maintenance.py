# utils/db_maintenance.py
"""
Automatic DB backup / restore for Secure-Chat.

Behaviour on server start:
1. If users.db is present and readable   → backup → proceed.
2. If users.db is missing or corrupted:
       • If any backup exists → restore newest backup.
       • Else                → create empty schema + bootstrap admin/admin.



        DB is present and valid	Nothing changes.
        DB is corrupted or deleted	Latest backup is restored (if found).
        No backup exists	New DB is created and admin/admin is inserted.
        All admins are deleted	admin/admin is reinserted automatically.
"""

import os, shutil, datetime, glob, sqlite3
from utils.db_setup import DB_PATH, init_user_db, _hash_password

MAX_BACKUPS = 5  # maximum number of backups
BACKUP_DIR = os.path.join(os.path.dirname(DB_PATH), "backup")
os.makedirs(BACKUP_DIR, exist_ok=True)

def _latest_backup() -> str | None:
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "users_*.sqlite")))
    return files[-1] if files else None

def _is_db_valid() -> bool:
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        ok = cur.fetchone() is not None
        conn.close(); return ok
    except Exception:
        return False

def ensure_db_ready():
    # 1) try current db
    if _is_db_valid():
        print("users.db OK")
    else:
        print("users.db missing or corrupted.")
        bk = _latest_backup()
        if bk:
            shutil.copy2(bk, DB_PATH)
            print(f" Restored latest backup → {bk}")
        else:
            print(" No backup found >> creating fresh DB with admin/admin.")
            init_user_db()
            _insert_bootstrap_account()

    # guarantee at least one admin
    _ensure_bootstrap_exists()

def _insert_bootstrap_account():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username,password,role) VALUES (?,?,?)",
        ("admin", _hash_password("admin"), "admin"),
    )
    conn.commit(); conn.close()

def _ensure_bootstrap_exists():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1")
    if not cur.fetchone():
        _insert_bootstrap_account()
        print(" Bootstrap admin/admin added (no admin found).")
    conn.close()

def backup_db() -> None:
    """
    Copy users.db into utils/backup/ with a timestamped filename.
    Afterward, prune old backups so only the newest MAX_BACKUPS remain.
    """
    # ── 1. create fresh backup 
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"users_{ts}.sqlite")
    shutil.copy2(DB_PATH, dst)
    print(f"Database backed up → {dst}")

    # ── 2. prune anything beyond MAX_BACKUPS 
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "users_*.sqlite")))         # glob.glob(...) returns a list of matching filenames
    while len(backups) > MAX_BACKUPS:                                               # sorted(...) puts them in ascending order → oldest file is first.
        oldest = backups.pop(0)          # first element = oldest thanks to sort()
        try:
            os.remove(oldest)
            print(f"Removed old backup {oldest}")
        except Exception as e:
            print(f"!!! Could not delete {oldest}: {e}")
