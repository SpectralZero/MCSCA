"""
Common helpers shared by the CTk demo UI.

• Finds the system Python 3.12 interpreter (PY312)
• Locates the folder that really holds secure_chat_*.py (CHAT_DIR)
• ROOT = project root (folder that contains ctk_gui/)
"""
from __future__ import annotations
import subprocess, sys, pathlib
from typing import Final

def _discover_py312() -> str:
    try:
        out = subprocess.check_output(
            ["py", "-3.12", "-c", "import sys;print(sys.executable)"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        if pathlib.Path(out).is_file():
            return out
    except Exception:
        pass
    exe = pathlib.Path(sys.executable)
    if exe.is_file():
        return str(exe)
    raise RuntimeError("Python 3.12 interpreter not found.")

PY312: Final[str] = _discover_py312()

# ── 2) repo root & chat-code folder ───────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parents[1]
def _find_chat_dir(root: pathlib.Path) -> pathlib.Path:
    for cand in (root, root / "Python"):
        if (cand / "secure_chat_server.py").is_file():
            return cand
    raise FileNotFoundError("secure_chat_server.py not found in project tree.")
CHAT_DIR: Final[pathlib.Path] = _find_chat_dir(ROOT)
# ── 3) Path to shared SQLite database ─────────────────────────────────
USERS_DB: Final[pathlib.Path] = ROOT / "utils" / "users.db"
# ── 4) Path to demo video for TLS App ──────────────────────────────────
VID: Final[pathlib.Path] = ROOT / "media" / "videos" / "SCA_demo" / "1080p60" / "JImSecureMessagingProtocol.mp4"
