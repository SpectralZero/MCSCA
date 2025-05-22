#!/usr/bin/env python3
"""
wipe_manager.py  ──  Global CleanupManager that always runs.
• Registers: WM_DELETE_WINDOW, console Ctrl-C, SIGTERM, WM_QUERYENDSESSION,
  atexit, sys.excepthook & threading.excepthook.
• Thread-safe idempotent (runs once).
"""
from __future__ import annotations
import os, sys, atexit, signal, traceback, threading, platform, ctypes, ctypes.wintypes
from typing import Iterable
from tools.wipe_core import shred_path, scrub_bytes, flush_clipboard

_APP_ROOT     = os.path.abspath(os.path.dirname(__file__))
_DEFAULT_PATHS = {
    os.path.join(_APP_ROOT, "logs"),
    os.path.join(_APP_ROOT, "tmp"),
    os.path.join(os.getenv("TEMP", "/tmp"), "secure_chat"),
}

# ------------------------------------------------------------------ #
#  ── Python 3.12 compatibility shim  (WNDCLASS vanished) ──────────────────
# ------------------------------------------------------------------ #
if os.name == "nt":
    import ctypes, ctypes.wintypes as _wt

    if not hasattr(_wt, "WNDCLASS"):
        # Define the missing Win32 struct by hand
        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style",        ctypes.c_uint),
                ("lpfnWndProc",  ctypes.c_void_p),   # will store a callback ptr
                ("cbClsExtra",   ctypes.c_int),
                ("cbWndExtra",   ctypes.c_int),
                ("hInstance",    ctypes.c_void_p),
                ("hIcon",        ctypes.c_void_p),
                ("hCursor",      ctypes.c_void_p),
                ("hbrBackground",ctypes.c_void_p),
                ("lpszMenuName", ctypes.c_wchar_p),
                ("lpszClassName",ctypes.c_wchar_p),
            ]
        _wt.WNDCLASS = WNDCLASS          # monkey-patch back into wintypes


WIPE_FILES = False      #  set to True if you ever want shredding again
      
class CleanupManager:
    _instance = None

    # ------------------------------------------------------------------ #
    def __new__(cls, *a, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_init_done", False): return
        self.paths: set[str] = set(_DEFAULT_PATHS)
        self.key_blobs: list[bytearray] = []
        self._lock = threading.Lock()
        self._ran  = False
        self._init_done = True
        self._register_hooks()

    # ------------ public API ---------------- #
    def add_paths(self, paths:Iterable[str]): self.paths.update(paths)
    def add_secret(self, secret:bytes|bytearray): self.key_blobs.append(bytearray(secret))

    # ------------ core wipe ------------------ #
    def wipe(self):
        with self._lock:
            if self._ran: return
            self._ran = True
            if WIPE_FILES:
                for p in list(self.paths):
                    try: shred_path(p)
                    except Exception: traceback.print_exc()
            for k in self.key_blobs:
                try: scrub_bytes(k)
                except Exception: pass
            flush_clipboard()

    # ------------ hook machinery ------------- #
    def _register_hooks(self):
        # Console signals
        signal.signal(signal.SIGINT,  self._sig_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._sig_handler)
        # Atexit fallback
        atexit.register(self.wipe)
        # Uncaught exceptions
        sys.excepthook = self._excepthook
        threading.excepthook = self._thread_excepthook
        # Windows shutdown / logoff
        #if platform.system() == "Windows":
            #self._install_win_shutdown_hook()

    # ------------------------------------------------------------------ #
    def _sig_handler(self, signum, frame):
        print(f"[CleanupManager] Signal {signum} caught – wiping…", file=sys.stderr)
        self.wipe(); sys.exit(0)

    def _excepthook(self, exc_type, exc, tb):
        traceback.print_exception(exc_type, exc, tb)
        self.wipe(); sys.exit(1)

    def _thread_excepthook(self, args):
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
        self.wipe(); sys.exit(1)

    # ---------------- Windows shutdown hook --------------------------- #
    def _install_win_shutdown_hook(self):
        user32 = ctypes.windll.user32
        kernel = ctypes.windll.kernel32
        WM_QUERYENDSESSION = 0x11
        WM_ENDSESSION      = 0x16
        WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_uint, ctypes.c_int, ctypes.c_int)

        def wnd_proc(hWnd, msg, wParam, lParam):
            if msg in (WM_QUERYENDSESSION, WM_ENDSESSION):
                self.wipe()
            return user32.DefWindowProcW(hWnd, msg, wParam, lParam)

        hInstance = kernel.GetModuleHandleW(None)
        class_name = "SecureChatHiddenWipeWnd"
        wndclass = ctypes.wintypes.WNDCLASS()
        wndclass.lpfnWndProc = WNDPROCTYPE(wnd_proc)
        wndclass.hInstance   = hInstance
        wndclass.lpszClassName = class_name
        atom = user32.RegisterClassW(ctypes.byref(wndclass))
        hwnd = user32.CreateWindowExW(0, atom, None, 0, 0,0,0,0, None, None, hInstance, None)
