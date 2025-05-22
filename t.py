# import requests

# def check_internet_via_http(url: str = "https://www.google.com", timeout: float = 3.0) -> bool:
#     """
#     Returns True if we can successfully perform a HEAD request to `url`.
#     """
#     try:
#         requests.head(url, timeout=timeout)
#         return True
#     except requests.RequestException:
#         return False
    
# print(f"Has internet: {check_internet_via_http()}")

# import socket
# import sys
# from tkinter import messagebox
# def check_internet_via_socket(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
#     """
#     Returns True if we can open a TCP connection to (host, port).
#     Default host=Google DNS, port=53.
#     """
#     try:
#         socket.setdefaulttimeout(timeout)
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#             sock.connect((host, port))
#         return True
#     except socket.error:
#         return False
    
# def ensure_online():
#     if not check_internet_via_socket():  # or check_internet_via_socket()
#         messagebox.showerror(
#             "No Internet Connection",
#             "Unable to reach the Internet.\n"
#             "Please check your network and try again."
#         )
#         sys.exit(1)

#     else:
#         print("Connected to the Internet.")    


# ensure_online()

# from SCA.tools.wipe_manager import CleanupManager
# print("Paths queued for wipe:")
# for p in CleanupManager().paths:
#     print(" ", p)
# import tempfile, logging, os, functools

# def log_temp_creation(func):
#     @functools.wraps(func)
#     def wrapper(*a, **kw):
#         path = func(*a, **kw)
#         if path.startswith(tempfile.gettempdir()):
#             logging.debug("Temp file created: %s", path)
#         return path
#     return wrapper

# # wrap high-risk APIs
# tempfile.NamedTemporaryFile = log_temp_creation(tempfile.NamedTemporaryFile)
# tempfile.mkstemp            = log_temp_creation(tempfile.mkstemp)

# import os, tempfile, time, psutil

# before = {f.path for f in os.scandir(tempfile.gettempdir())}
# print("Watch started – launch your chat client now...")
# time.sleep(60)   # give yourself a minute to test chat actions
# after = {f.path for f in os.scandir(tempfile.gettempdir())}

# new_files = after - before
# print("New temp artefacts:")
# for p in new_files:
#     print(" ", p)
import subprocess, time, pyperclip, os, sys, signal

SCRIPT = r"C:\Users\RTX\Desktop\EA\SCA\secure_chat_client1.py"   # <- full path
SERVER = "localhost"
PORT_S = "4444"
PORT_C = "2246"

# 1) prime the clipboard
pyperclip.copy("SENSITIVE")

# 2) launch Secure-Chat
proc = subprocess.Popen(
    [sys.executable, SCRIPT, SERVER, PORT_S, PORT_C],
    cwd=os.path.dirname(SCRIPT)
)

print("Client started (PID", proc.pid, ") – close the GUI window manually…")
proc.wait()                         # wait for graceful GUI close

# 3) give Python a moment to run atexit hooks
time.sleep(1.0)

# 4) test clipboard
assert pyperclip.paste() == "", "Clipboard not cleared!"
print("✔ Clipboard successfully wiped")