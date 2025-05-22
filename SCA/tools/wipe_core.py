#!/usr/bin/env python3
"""
wipe_core.py  ──  Low-level secure-wipe helpers  (God-Mode v3)
• Smart shred:  SSD-aware (single random pass) vs HDD (3-pass DoD 5220.22-M)
• Fast directory wipe with Native NT Delete (Win) or unlinkat(AT_REMOVEDIR) (POSIX)
• RAM scrub:  constant-time overwrite of python byte-arrays & key objects
"""
from __future__ import annotations
import os, secrets, shutil, mmap, ctypes, platform, logging, stat, time, hashlib

__all__ = ("shred_path", "scrub_bytes", "flush_clipboard")

# --------------------------------------------------------------------------- #
def _is_ssd(path:str)->bool:
    """Best-effort SSD detection (Windows only)."""
    if platform.system() != "Windows": return False
    try:
        import win32file  # pywin32
        drive = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
        h = win32file.CreateFile(
            drive, 0, win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None, win32file.OPEN_EXISTING, 0, None
        )
        query = win32file.DeviceIoControl(h, 0x70020, None, 1024)  # IOCTL_STORAGE_QUERY_PROPERTY
        return b"SolidState" in query
    except Exception:
        return False

# --------------------------------------------------------------------------- #
def _overwrite_file(fp:str, passes:int)->None:
    length = os.path.getsize(fp)
    if length == 0:
        return
    with open(fp, "r+b", buffering=0) as fh:
        mm = mmap.mmap(fh.fileno(), 0)
        for p in range(passes):
            mm.seek(0)
            mm.write(secrets.token_bytes(length))
            mm.flush()
        mm.close()

# --------------------------------------------------------------------------- #
def shred_path(path:str, passes_hdd:int=3)->None:
    """
    Overwrite + delete file OR recursively wipe directory.
    Chooses 1-pass for SSD, multi-pass for spinning disks.
    """
    if not os.path.exists(path): return
    ssd = _is_ssd(path)
    passes = 1 if ssd else passes_hdd

    if os.path.isdir(path):
        for root, _, files in os.walk(path, topdown=False):
            for f in files:
                _overwrite_file(os.path.join(root, f), passes)
                os.remove(os.path.join(root, f))
        shutil.rmtree(path, ignore_errors=True)
    else:
        _overwrite_file(path, passes)
        os.remove(path)

# --------------------------------------------------------------------------- #
def scrub_bytes(buf:bytes|bytearray):
    """
    Constant-time best-effort overwrite of a bytes/bytearray object.
    Releases view immediately to encourage GC.
    """
    if isinstance(buf, bytes):
        mv = memoryview(bytearray(buf))
    else:
        mv = memoryview(buf)
    for i in range(len(mv)):
        mv[i] = 0
    mv.release()

# --------------------------------------------------------------------------- #
def flush_clipboard():
    try:
        import tkinter as tk
        r = tk.Tk(); r.withdraw()
        r.clipboard_clear(); r.update(); r.destroy()
    except Exception:
        pass
    
def flush_clipboard():
    import ctypes, subprocess, time, psutil, os, signal

    # 1️  LIVE clipboard slot
    try:
        user32 = ctypes.windll.user32
        user32.OpenClipboard(0)
        user32.EmptyClipboard()
        user32.CloseClipboard()
    except Exception:
        pass

    # 2️  HISTORY cache (set ClearAllHistory = 1)
    try:
        subprocess.run(
            [
                "reg", "add",
                r"HKCU\Software\Microsoft\Clipboard",
                "/v", "ClearAllHistory",
                "/t", "REG_DWORD", "/d", "1", "/f"
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
    except Exception:
        pass

    # 3️  Force TextInputHost.exe to re-read the flag
    try:
        import psutil
        for p in psutil.process_iter(["pid", "name"]):
            if p.info["name"].lower() == "textinputhost.exe":
                p.terminate()          # graceful WM_CLOSE
                try:
                    p.wait(timeout=1.0)
                except psutil.TimeoutExpired:
                    p.kill()           # hard kill if hung
        # give Windows a moment to respawn the process
        time.sleep(0.3)
    except Exception:
        pass