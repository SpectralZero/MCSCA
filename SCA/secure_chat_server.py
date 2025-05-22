#!/usr/bin/env python
"""
Secure-Chat Server
──────────────────
• TLS-wrapped socket
• Username/password + USB 2-factor
• 3-strike login throttle (IP-based, RAM-only)
• Broadcast + private messages
"""
from __future__ import annotations
import errno, signal, socket, ssl, sys, threading, time, sqlite3 #  errno = OS‐level error codes
from contextlib import closing
from typing import Dict, Tuple

import base64, os                                  
from security import (                              
    encrypt_message, decrypt_message,
    generate_ecdh_keypair, derive_shared_key
)

from logging_config import setup_logging
from utils.tls_setup import ensure_cert_in_cert_dir, configure_tls_context
from utils.db_setup    import init_user_db, verify_credentials, DB_PATH
from utils.db_maintenance import ensure_db_ready, backup_db

# ── globals ──────────────────────────────────────────────────────────
logger = setup_logging()
init_user_db()                                    # ensure users.db exists

connected_clients: Dict[str, Tuple[socket.socket, Tuple[str, int]]] = {}
_clients_lock = threading.RLock()

PORT_DEFAULT        = 4444
MAX_MSG_LEN         = 64 * 1024
SOCKET_TIMEOUT_SECS = 30

# USB 2FA
_MAX_FAILS_USB      = 3
_LOCK_SECS_USB      = 240

# login-throttling (username/password stage)
_MAX_LOGIN_FAILS    = 3
_LOCK_SECS_LOGIN    = 300          # 5 minutes
_login_fails: dict[str, tuple[int, int]] = {}    # ip -> (fails, locked_until)
_login_lock = threading.RLock()
# ─────────────────────────────────────────────────────────────────────

# ──  helpers ────────────────────────────────────────────────
def _is_locked(ip: str) -> int:
    with _login_lock:
        cnt, locked_until = _login_fails.get(ip, (0, 0))
    return max(0, locked_until - int(time.time()))

def _register_fail(ip: str) -> int:
    """Increment fail count, return tries_left (0 if now locked)."""
    now = int(time.time())
    with _login_lock:
        cnt, locked_until = _login_fails.get(ip, (0, 0)) # cnt = count of failed attempts, locked_until = time when the user will be unlocked :( 
        if locked_until > now:             # still locked
            return 0
        cnt += 1
        if cnt >= _MAX_LOGIN_FAILS:
            _login_fails[ip] = (0, now + _LOCK_SECS_LOGIN) # reset count to 0, set a new lockout window (now + LOCK_SECS)
            return 0
        _login_fails[ip] = (cnt, 0)
        return _MAX_LOGIN_FAILS - cnt

def _clear_fail(ip: str) -> None:
    with _login_lock:
        _login_fails.pop(ip, None)

# ── bootstrap ───────────────────────────────────────────────────────
def start_server(port: int = PORT_DEFAULT) -> None:
    ensure_db_ready()
    backup_db()

    # keep existing cert; generate only if missing
    cert_path, key_path = ensure_cert_in_cert_dir("server_cert.pem",
                                                  "server_key.pem")
    tls_ctx = configure_tls_context(certfile=cert_path, keyfile=key_path,
                                    purpose=ssl.Purpose.CLIENT_AUTH)

    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    raw.bind(("0.0.0.0", port))
    raw.listen(100)
    logger.info("Secure-Chat Server listening on 0.0.0.0:%s", port)

    server_sock = tls_ctx.wrap_socket(raw, server_side=True)
    signal.signal(signal.SIGINT, lambda *_: shutdown(server_sock))

    while True:
        try:
            cli_sock, cli_addr = server_sock.accept()
        except ssl.SSLError as e:
            logger.warning("TLS handshake failed: %s", e);  continue
        except OSError as e:
            if e.errno == errno.EBADF: break       # listener closed (shutdown()), a socket.timeout will be raised.
            logger.error("Accept failed: %s", e);  continue

        logger.info("Connection from %s", cli_addr)
        threading.Thread(target=handle_client,
                         args=(cli_sock, cli_addr),
                         daemon=True).start()

# ── per-client thread ───────────────────────────────────────────────
def handle_client(sock: ssl.SSLSocket, addr) -> None:
    sock.settimeout(SOCKET_TIMEOUT_SECS) # client is idle for 30 seconds
    ip = addr[0] # IP address of the client 
    username = None
    try:
        # 0) lock-out check before reading anything
        wait = _is_locked(ip)
        if wait:
            _send_prefixed(sock, f"LOCKED {wait}".encode())
            return

        # 1) username / password -------------------------------------
        creds = _recv_prefixed(sock)
        if not creds or b":" not in creds:
            _send_prefixed(sock, b"FAIL");  return
        username, password = creds.decode().split(":", 1)
        if not verify_credentials(username, password):
            left = _register_fail(ip)
            if left:
                _send_prefixed(sock, f"LOGINFAIL {left}".encode())
            else:
                _send_prefixed(sock, f"LOCKED {_LOCK_SECS_LOGIN}".encode())
            return
        _clear_fail(ip)                     # good credentials

        # 2) USB 2-factor loop ---------------------------------------
        _send_prefixed(sock, b"USBREQ")
        while True:
            usb = _recv_prefixed(sock)
            if not usb or b":" not in usb:
                _send_prefixed(sock, b"FAIL");  return
            serial, digest = usb.decode().split(":", 1)
            ok, wait, tries_left = _verify_usb(username, serial, digest) # USB check from DB
            if ok:
                break
            if wait:
                _send_prefixed(sock, f"LOCKED {wait}".encode())
                return
            _send_prefixed(sock, f"USBFAIL {tries_left}".encode())

        _send_prefixed(sock, b"SUCCESS")    # USB OK
        
        # 3) expect KEYPUB
        pubpkt = _recv_prefixed(sock)
        if not pubpkt.startswith(b"KEYPUB "):
            logger.error("Keypub missing from %s", username); return
        pub_b64 = pubpkt.split(b" ",1)[1].decode() # [1] base64-encoded public key 
      
        # 3) mark online / notify others -----------------------------
        with _clients_lock:
            """
              Once a user passes both password and USB checks, 
              add them to the server's active-clients map,
              tell their client 'you're in,' update everyone's user list, and log it.
            """
            connected_clients[username] = (sock, addr, pub_b64)       
        _send_prefixed(sock, b"SUCCESS")    # full login OK
        _broadcast_user_list()
        _send_existing_keypubs(sock)                # give newcomer others
        _broadcast_keypub(username, pub_b64)        # tell others newcomer
        logger.info("[%s] logged in as '%s'", addr, username)
        logger.info("[%s] authenticated as '%s'", addr, username)

        # 4) chat loop -----------------------------------------------
        while True:
            frame = _recv_prefixed(sock)
            if not frame: break
            if frame == b"PING": continue
            if frame.startswith(b"BCAST "):
                _route_broadcast(frame); continue
            if frame.startswith(b"CIPH "):
                _route_cipher(frame); continue
            
            token = frame.split(b" ", 1)[0]

            # If it’s any of our file-transfer types, relay it:
            if token in (b"FILE_OFFER", b"FILE_CHUNK", b"FILE_COMPLETE", b"FILE_CANCEL"):
                # parts = [TYPE, sender, recipient, payload]
                parts     = frame.split(b" ", 3)
                recipient = parts[2].decode()
                target    = connected_clients.get(recipient)
                if target:
                    _send_prefixed(target[0], frame)
                # skip further handling
                continue
            

    except socket.timeout:
        logger.info("%s timed out.", username or addr)
    except (ConnectionResetError, BrokenPipeError):
        logger.info("%s disconnected abruptly.", username or addr)
    except Exception as e:
        logger.error("Unhandled error with %s: %s", addr, e)
    finally:
        with _clients_lock:
            connected_clients.pop(username, None)
        _broadcast_user_list()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        sock.close()
        logger.info("Client '%s' disconnected.", username or addr)

def _send_existing_keypubs(sock):
    with _clients_lock:
        for user, (_,_,pub) in connected_clients.items():
            _send_prefixed(sock, f"KEYPUB {user} {pub}".encode())

def _broadcast_keypub(user, pub_b64):
    pkt = f"KEYPUB {user} {pub_b64}".encode()
    with _clients_lock:
        for u,(s,_,_) in connected_clients.items(): # u = username, s = socket, _ _ ignore the rest of the tuple
            if u != user: _send_prefixed(s, pkt) # ensures that the public key is not sent back to the user who owns it

def _route_cipher(frame: bytes):
        # frame = b"CIPH <sender> <recipient> <base64_blob>"
    parts = frame.split(b" ", 3) # parts = [b"CIPH", b"sender", b"recipient", b"blob"]
    if len(parts) != 4:
        return
    _, sender_b, recipient_b, blob_b64 = parts
    sender    = sender_b.decode()
    recipient = recipient_b.decode()
    # ───────── NEW logging ─────────
    logger.info(
        "Relaying E2E private message from %s to %s: %s",
        sender, recipient, blob_b64.decode()
    )
    # ───────── existing relay ─────────
    tgt = connected_clients.get(recipient)
    if not tgt:
        return
    _send_prefixed(tgt[0], frame)

def _route_broadcast(frame: bytes):
    # frame = b"BCAST sender blob"
    parts = frame.split(b" ", 2) # parts = [b"BCAST", b"sender", b"blob"]
    if len(parts) != 3:
        return
    _, sender_b, blob_b64 = parts
    sender = sender_b.decode()

    with _clients_lock:
        for uname, (sock, _, _) in connected_clients.items():
            if uname == sender:
                continue      # don't send back to the originator
            _send_prefixed(sock, frame)

# ── USB verification ────────────────────────────────────────────────
def _verify_usb(user: str, serial: str, digest: str) -> tuple[bool, int, int]:
    """Return (ok, seconds_left_if_locked, tries_left_if_fail)."""
    now = int(time.time())
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cur = conn.cursor()
        cur.execute("""SELECT usb_serial, usb_hash,
                              usb_fail_count, usb_locked_until
                       FROM users WHERE username=?""", (user,))
        row = cur.fetchone()
        if not row or not row[0]:
            return False, 0, 0
        exp_serial, exp_hash, fails, locked = row
        if locked and locked > now:
            return False, locked - now, 0

        # success?
        if serial == exp_serial and digest.lower() == exp_hash.lower():
            cur.execute("""UPDATE users
                             SET usb_fail_count=0, usb_locked_until=0
                           WHERE username=?""", (user,))
            return True, 0, 0

        # failure
        fails += 1
        new_lock = now + _LOCK_SECS_USB if fails >= _MAX_FAILS_USB else 0
        cur.execute("""UPDATE users
                         SET usb_fail_count=?, usb_locked_until=?
                       WHERE username=?""",
                    (fails % _MAX_FAILS_USB, new_lock, user))
        tries_left = 0 if new_lock else (_MAX_FAILS_USB - fails)
        return False, new_lock - now if new_lock else 0, tries_left

# ── tiny helpers ----------------------------------------------------
def _read_exact(sock: socket.socket, n: int) -> bytes:   # n = number of bytes to read.
    """Ensure you read exactly n bytes from the socket (looping on partial reads), 
       or return an empty bytes object if the connection closes.
       
       (Reads exactly n bytes from the socket Keep reading until you have all n bytes.(or returns empty if the connection closed).
       """
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return b""
        data += chunk
    return data

def _recv_prefixed(sock: socket.socket) -> bytes:
    """
        Read a 4-byte big-endian length header, validate it,  
        then read that many bytes—delivering one complete framed message.
        (Reads a 4-byte length, then reads exactly that many bytes to get one complete message.)
        >>First read 4 bytes to know how big the message is.
        >>Then read exactly that many bytes to get the full message.
        >>If anything is wrong (invalid size), return empty b"".
    """
    hdr = _read_exact(sock, 4)  # hdr =  4-byte length prefix of the message.
    if not hdr:
        return b""
    length = int.from_bytes(hdr, "big")
    if length <= 0 or length > MAX_MSG_LEN:
        return b""
    return _read_exact(sock, length)

def _send_prefixed(sock: socket.socket, payload: bytes) -> None:
    """
        Prepend a 4-byte big-endian length header to payload and send it in one sendall() call,
        ensuring the receiver can parse message boundaries.

        (Sends your data with a 4-byte length header so the receiver knows where the message ends.)
        Goal: Send a message with a 4-byte length prefix.

        First attach the message size (4 bytes).

        Then send both together in one sendall() call.
    """
    try:
        sock.sendall(len(payload).to_bytes(4, "big") + payload)
    except Exception as e:
        logger.debug("send failed: %s", e)

def _broadcast_user_list() -> None:
    with _clients_lock:
        users_csv = ",".join(connected_clients.keys())
        targets   = [t[0] for t in connected_clients.values()]   # take only the socket
    msg = f"USERS {users_csv}".encode()
    for s in targets:
        _send_prefixed(s, msg)

def broadcast(msg: str, *, exclude: str | None = None) -> None: # * = no more positional arguments after this, 
    """
    Send a message to all clients (except maybe one client if exclude is given)
    For each connected client:

    If it's not the excluded user, send the message.

    If sending fails, mark them as "dead" (disconnected).

    If any clients are "dead," close their sockets and remove them from the connected users list.

    Then update everyone again with the new user list.
    """
    dead = []
    with _clients_lock:
        items = list(connected_clients.items())
    for user, (s, _) in items:
        if user == exclude:
            continue
        try:
            _send_prefixed(s, msg.encode())
        except Exception as e:
            logger.warning("Broadcast to %s failed: %s", user, e)
            dead.append(user)
    if dead:
        with _clients_lock:
            for u in dead:
                try:
                    connected_clients[u][0].close()
                except Exception:
                    pass
                connected_clients.pop(u, None)
        _broadcast_user_list()

# ── graceful shutdown ----------------------------------------------
def shutdown(server_sock: ssl.SSLSocket) -> None:
    logger.info("Shutting down server …")
    try:
        server_sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    server_sock.close()
    with _clients_lock:
        for s, _ in connected_clients.values():
            try:
                s.close()
            except Exception:
                pass
        connected_clients.clear()
    sys.exit(0)

# ── entrypoint ------------------------------------------------------
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) == 2 else PORT_DEFAULT
    start_server(port)
