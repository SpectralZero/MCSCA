"""
core.secure_delete
──────────────────
Military-grade file & directory shredder (cross-platform).

Features
▪ Multi-pass overwrite with rename-scramble and fsync.
▪ Symbolic-/hard-link refusal (prevents by-reference wipes).
▪ Optional “save shredded bytes” tree replica.
▪ SSD detection + NIST SP-800-88 warning.
▪ Headless API: returns (True, detail:str) on success.

Typical use
───────────
from core.secure_delete import shred_file
ok, info = shred_file("secret.docx", passes=3)
"""

from __future__ import annotations

import os
import shutil
import secrets
import logging
import platform
from pathlib import Path
from typing import Callable, Optional, Tuple

__all__ = [
    "ShredError",
    "shred_file",
    "shred_directory",
]

LOG = logging.getLogger("secure_delete")
LOG.addHandler(logging.NullHandler())


# ────────────────────────────────────────────────────────────────────────────────
# Exceptions
# ────────────────────────────────────────────────────────────────────────────────
class ShredError(RuntimeError):
    """Base class for secure-delete failures."""


# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────
_BUFFER = 1 << 16  # 64 KiB


def _secure_rename(path: Path) -> Path:
    """Rename *path* atomically to a random filename in the same directory."""
    rand = "~" + secrets.token_hex(8)
    new_path = path.with_name(rand)
    os.replace(path, new_path)
    return new_path


def _looks_like_ssd(path: Path) -> bool:
    """Best-effort heuristic to tell if *path* lives on a non-rotational device."""
    try:
        if platform.system() == "Windows":
            import ctypes.wintypes as wt

            kernel32 = ctypes.windll.kernel32  # type: ignore
            handle = kernel32.CreateFileW(
                str(path.drive),
                0,
                0,
                None,
                3,  # OPEN_EXISTING
                0,
                None,
            )
            # 0x90000 == FILE_DEVICE_FILE_SYSTEM; unreadable w/o admin → assume HDD
            if handle == -1:
                return False
            is_ssd = ctypes.c_ulong()
            kernel32.DeviceIoControl(
                handle,
                0x00070180,  # IOCTL_STORAGE_QUERY_PROPERTY(DeviceSeekPenaltyProperty)
                None,
                0,
                ctypes.byref(is_ssd),
                ctypes.sizeof(is_ssd),
                ctypes.byref(ctypes.c_ulong()),
                None,
            )
            kernel32.CloseHandle(handle)
            return not bool(is_ssd.value)
        else:  # Linux / macOS
            block = Path(path.anchor).parts[0]  # '/' on *nix
            rotational = Path(f"/sys/block/{block}/queue/rotational")
            return rotational.exists() and rotational.read_text().strip() == "0"
    except Exception:  # pragma: no cover
        return False


def _is_subdir(child: Path, parent: Path) -> bool:
    """Return True if *child* is the same as or inside *parent*."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _overwrite(
    file: Path,
    passes: int,
    bufsize: int,
    progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    size = file.stat().st_size
    with file.open("r+b", buffering=0) as fh:
        for p in range(1, passes + 1):
            fh.seek(0)
            written = 0
            pattern_byte = bytes([p % 256])
            while written < size:
                chunk = min(bufsize, size - written)
                data = os.urandom(chunk) if p == passes else pattern_byte * chunk
                fh.write(data)
                written += chunk
            fh.flush()
            os.fsync(fh.fileno())
            if progress:
                progress(p, passes)


# ────────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────────
def shred_file(
    path: str | os.PathLike,
    *,
    passes: int = 3,
    keep_bytes: bool = False,
    keep_root: Optional[str | os.PathLike] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Tuple[bool, str]:
    """
    Securely overwrite *path* and optionally move the bytes to *keep_root*.

    Parameters
    ----------
    passes        : overwrite passes (NIST recommends 1 random pass for modern drives)
    keep_bytes    : if True, move the final “garbled” file instead of deleting
    keep_root     : directory where garbled files land (tree preserved)
    progress(p,t) : optional callback after each pass

    Returns
    -------
    success, message
    """
    path = Path(path)
    try:
        if not path.exists():
            raise ShredError("target does not exist")

        if path.is_symlink():
            raise ShredError("refusing to shred symbolic link")

        if path.stat().st_nlink > 1:
            raise ShredError("refusing to shred hard-linked file")

        if passes < 1 or passes > 35:
            raise ValueError("passes must be 1-35")

        # SSD warning (best-effort)
        if _looks_like_ssd(path):
            LOG.warning("Device looks like SSD; overwrite may be ineffective.")

        scrambled = _secure_rename(path)
        _overwrite(scrambled, passes, _BUFFER, progress)

        if keep_bytes:
            if not keep_root:
                raise ShredError("keep_root must be set when keep_bytes=True")
            keep_root = Path(keep_root).expanduser().absolute()
            rel = scrambled.name if keep_root == scrambled.parent else scrambled.relative_to(scrambled.anchor)
            dst = keep_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(scrambled), str(dst))
            return True, f"shredded and moved to {dst}"
        else:
            scrambled.unlink()
            return True, "shredded & deleted"
    except Exception as exc:
        LOG.exception("shred_file failed: %s", exc)
        return False, f"shred error: {exc}"


def shred_directory(
    directory: str | os.PathLike,
    *,
    passes: int = 3,
    keep_bytes: bool = False,
    keep_root: Optional[str | os.PathLike] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Tuple[bool, str]:
    """
    Recursively shred all files in *directory*.

    *keep_root* must not be inside *directory*.
    Progress callback receives overall completed passes, total passes.
    """
    directory = Path(directory)
    try:
        if not directory.is_dir():
            raise ShredError("target is not a directory")

        if keep_bytes and keep_root and _is_subdir(keep_root, directory):
            raise ShredError("keep_root cannot be inside target directory")

        files = [p for p in directory.rglob("*") if p.is_file()]
        total_passes = len(files) * passes
        done = 0

        for f in files:

            def _file_cb(cur: int, tot: int) -> None:
                nonlocal done
                done_pass = cur
                progress(done + done_pass, total_passes) if progress else None

            ok, _ = shred_file(
                f,
                passes=passes,
                keep_bytes=keep_bytes,
                keep_root=keep_root,
                progress=_file_cb,
            )
            if not ok:
                raise ShredError(f"failed on {f}")
            done += passes

        if not keep_bytes:
            shutil.rmtree(directory)
        return True, "directory shredded"
    except Exception as exc:
        LOG.exception("shred_directory failed: %s", exc)
        return False, f"dir-shred error: {exc}"
