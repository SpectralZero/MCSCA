# core/api.py  ───────────────────────────────────────────
"""
Tiny shim that the GUI calls.

Later you can redirect each function to your real
secure_chat_server / client code.
"""

_running = False
_users   = [ "jamal", "ahmad", "mubarak" ]
_logs    = []

def _log(msg): _logs.append(msg)

# ── server control ──────────────────────────────────────
def start_server():
    global _running
    _running = True
    _log("server started")
    return True

def stop_server():
    global _running
    _running = False
    _log("server stopped")
    return True

def is_server_running(): return _running

# ── messaging  ──────────────────────────────────────────
def broadcast(msg):             _log(f"[BCAST] {msg}")
def send_private(to, msg):      _log(f"[PM →{to}] {msg}")
def get_user_list():            return _users

# ── logs  ───────────────────────────────────────────────
def tail_logs(n=500):           return _logs[-n:]

# ── user DB CRUD  ───────────────────────────────────────
import hashlib, os, itertools
_user_db = { u: hashlib.sha256(u.encode()).hexdigest() for u in _users }

def add_user(u,p):
    if u in _user_db: return False
    _user_db[u] = hashlib.sha256(p.encode()).hexdigest()
    return True

def delete_user(u):  _user_db.pop(u, None)
def list_users():    return list(_user_db.items())

# ── feature toggles ─────────────────────────────────────
_tls = True; _usb = False; _tor = False
def is_tls_enforced():  return _tls
def set_tls_enforced(b):  global _tls; _tls = b
def is_usb_required():  return _usb
def set_usb_required(b):  global _usb; _usb = b
def is_tor_allowed():   return _tor
def set_tor_allowed(b):  global _tor; _tor = b
