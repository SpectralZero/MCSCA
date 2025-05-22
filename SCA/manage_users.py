#!/usr/bin/env python
"""
manage_users.py – add / update / delete users and program USB sticks (DB‑only)
"""
import argparse, os, hashlib, secrets, sqlite3, sys, win32api
from utils.db_setup import _hash_password, DB_PATH

def _serial(drive):   
    if not drive.endswith("\\"): drive += "\\"
    return str(win32api.GetVolumeInformation(drive)[1])

def _write_key(drive):
    secret = secrets.token_bytes(32)
    open(os.path.join(drive, "key.dat"), "wb").write(secret)
    return hashlib.sha256(secret).hexdigest()

def program_usb(username, drive):
    serial = _serial(drive); h = _write_key(drive)
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("UPDATE users SET usb_serial=?, usb_hash=? WHERE username=?", (serial, h, username))
    if cur.rowcount==0: sys.exit("User not found in DB.")
    conn.commit(); conn.close()
    print(f"USB programmed. Serial={serial}")

def add(user, pwd, drive):
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("INSERT INTO users (username,password) VALUES (?,?)", (user,_hash_password(pwd))); conn.commit(); conn.close()
    program_usb(user, drive)

def update(user, pwd, drive):
    if pwd:
        conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
        cur.execute("UPDATE users SET password=? WHERE username=?", (_hash_password(pwd),user)); conn.commit(); conn.close()
    if drive: program_usb(user, drive)

def delete(user):
    conn=sqlite3.connect(DB_PATH); cur=conn.cursor()
    cur.execute("DELETE FROM users WHERE username=?", (user,)); conn.commit(); conn.close()
    print("User deleted.")

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("add");    p.add_argument("--user"); p.add_argument("--password"); p.add_argument("--drive")
    p=sub.add_parser("update"); p.add_argument("--user"); p.add_argument("--password"); p.add_argument("--drive")
    p=sub.add_parser("delete"); p.add_argument("--user")
    args=ap.parse_args()
    if args.cmd=="add": add(args.user,args.password,args.drive)
    elif args.cmd=="update": update(args.user,args.password,args.drive)
    else: delete(args.user)
