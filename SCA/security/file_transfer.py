import os
import threading
import base64
import math
import json
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from uuid import uuid4
import customtkinter as ctk
from tkinter import messagebox
from security import encrypt_message, decrypt_message

CHUNK_SIZE = 16 * 1024  # 16 KB per chunk

class FileTransferManager:
    """
    Manages end-to-end encrypted file transfers over the existing TLS channel.
    Attach to ChatClient and GUI to handle sending and receiving files.
    """
    def __init__(self, chat_client, gui):
        self.chat_client = chat_client  # instance of ChatClient
        self.gui = gui                  # reference to GUI controller (e.g., root window)
        self.incoming = {}              # file_id -> metadata + chunks
        self.pending = {}               # file_id -> list of chunk JSON strings

    def send_file(self, file_path: str, recipient: str):
        """
        Initiate a secure, end-to-end encrypted file send:
        1. Verify shared key exists
        2. Send the FILE_OFFER metadata
        3. Launch background thread to stream FILE_CHUNK frames
        """
        # --- 0) Fetch & verify the 32-byte AES-GCM key ---
        key = self.chat_client.get_shared_key(recipient)
        if len(key) != 32:
            messagebox.showerror(
                "Encryption Key Missing",
                "No shared encryption key for that user yet.\n"
                "Wait until they complete key exchange."
            )
            return

        # --- 1) Prepare metadata offer ---
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_id   = str(uuid4()) # (Universally Unique Identifier) make a unique ID for this file , to ensure no collisions with others on the network
        offer = {
            "type":      "FILE_OFFER",
            "file_id":   file_id,
            "file_name": file_name,
            "file_size": file_size
        }

        # --- 2) Encrypt & send FILE_OFFER ---
        payload = json.dumps(offer)
        blob    = encrypt_message(key, payload) 
        frame   = (
            b"FILE_OFFER " +
            self.chat_client.username.encode() + b" " +
            recipient.encode() + b" " +
            base64.b64encode(blob)
        ) 
        self.chat_client._send_prefixed(frame)

        # --- 3) Show in sender GUI ---
        self.gui.add_sent_file_message(file_id, file_name, file_size)

        # --- 4) Launch chunk sender thread ---
        threading.Thread(
            target=self._send_chunks,
            args=(file_path, file_id, recipient),
            daemon=True,
            name=f"ft_send_{file_id[:8]}"
        ).start()

    def _send_chunks(self, file_path: str, file_id: str, recipient: str):
            """
            Read the file in CHUNK_SIZE slices, encrypt each chunk as a JSON string,
            and send it over the existing TLS socket.  On error, send a FILE_CANCEL.
            Base64-encodes chunk → JSON → encrypt → send.
            Each chunk is:

            individually encrypted

            encoded safely for JSON and base64
            """
            key = self.chat_client.get_shared_key(recipient)
            try:
                with open(file_path, "rb") as f:
                    index = 0
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        # Build the chunk payload
                        msg = {
                            "type":    "FILE_CHUNK",
                            "file_id": file_id,
                            "index":   index,
                            # base64-encode to JSON-safe text
                            "data":    base64.b64encode(chunk).decode()
                        }

                        # **Pass a str** to encrypt_message
                        payload = json.dumps(msg)
                        blob    = encrypt_message(key, payload)

                        # Frame = TYPE sender recipient base64(blob)
                        frame = (
                            b"FILE_CHUNK " +
                            self.chat_client.username.encode() + b" " +
                            recipient.encode() + b" " +
                            base64.b64encode(blob)
                        )
                        self.chat_client._send_prefixed(frame)
                        index += 1

                        complete = {"type":"FILE_COMPLETE", "file_id":file_id}
                        payload  = json.dumps(complete)
                        blob     = encrypt_message(key, payload)
                        frame    = (
                            b"FILE_COMPLETE " +
                            self.chat_client.username.encode() + b" " +
                            recipient.encode() + b" " +
                            base64.b64encode(blob)
                        )
                        self.chat_client._send_prefixed(frame)


            except Exception as e:
                # On any error, notify the recipient that this transfer was canceled
                cancel = {
                    "type":    "FILE_CANCEL",
                    "file_id": file_id,
                    "reason":  str(e)
                }

                # Again, pass str into encrypt_message—no .encode() here
                payload = json.dumps(cancel)
                blob    = encrypt_message(key, payload)

                frame = (
                    b"FILE_CANCEL " +
                    self.chat_client.username.encode() + b" " +
                    recipient.encode() + b" " +
                    base64.b64encode(blob)
                )
                self.chat_client._send_prefixed(frame)

    def download_file(self, file_id: str):
        entry = self.incoming.get(file_id)
        if not entry or not entry["complete"]:
            mb.showinfo("Download", "File not fully received yet.")
            return

        # ask user where to save
        path = fd.asksaveasfilename(
            title="Save file as…",
            initialfile=entry["name"]
        )
        if not path:
            return

        # disable the button immediately
        self.chat_client.master.after(0,
            lambda: self.chat_client.set_download_state(file_id, text="0%", state="disabled")
        )

        def _worker():
            total_chunks = math.ceil(entry["size"] / CHUNK_SIZE)
            try:
                with open(path, "wb") as out:
                    for idx in range(total_chunks):
                        out.write(entry["chunks"][idx])
                        # compute percent
                        pct = int((idx+1) * 100 / total_chunks)
                        # schedule UI update
                        self.chat_client.master.after(0,
                            lambda p=pct: self.chat_client.set_download_state(
                                file_id,
                                text=f"{p}%",
                                state="disabled"
                            )
                        )
                # open file automatically if desired
                if os.name == "nt":
                    os.startfile(path)
                else:
                    from subprocess import call
                    call(["xdg-open", path])
            except Exception as e:
                mb.showerror("Error Saving File", str(e))
            finally:
                # always re-enable the button at 100%
                self.chat_client.master.after(0,
                    lambda: self.chat_client.set_download_state(
                        file_id,
                        text="⬇ Download",
                        state="normal"
                    )
                )
                mb.showinfo("Download Complete", f"Saved to {path}")

        threading.Thread(target=_worker, daemon=True).start()

    def download_file(self, file_id: str):
        entry = self.incoming.get(file_id)
        if not entry or not entry["complete"]:
            mb.showinfo("Download", "File not fully received yet.")
            return

        # ask user where to save
        path = fd.asksaveasfilename(
            title="Save file as…",
            initialfile=entry["name"]
        )
        if not path:
            return

        try:
            total_chunks = math.ceil(entry["size"] / CHUNK_SIZE)
            with open(path, "wb") as out:
                for idx in range(total_chunks):
                    out.write(entry["chunks"][idx])
            # optionally open it:
            if os.name == "nt":
                os.startfile(path)
            else:
                from subprocess import call
                call(["xdg-open", path])
        except Exception as e:
            mb.showerror("Error Saving File", str(e))
        else:
            mb.showinfo("Download Complete", f"Saved to {path}")
    def handle_frame(self, frame_type, sender, blob_b64):
        # Called from ChatClient._recv_loop for file-related frames
        key = self.chat_client.get_shared_key(sender)
        try:
            raw = base64.b64decode(blob_b64)
            plaintext = decrypt_message(key, raw)
            data = json.loads(plaintext)
        except Exception:
            return  # decryption/parsing failed

        typ = data.get("type")
        if typ == "FILE_OFFER":
            self._on_offer(data)
        elif typ == "FILE_CHUNK":
            self._on_chunk(data)
        elif typ == "FILE_CANCEL":
            self._on_cancel(data)

    def _on_offer(self, offer):
        fid = offer["file_id"]
        self.incoming[fid] = {
            "name": offer["file_name"],
            "size": offer["file_size"],
            "chunks": {},
            "received": 0,
            "complete": False
        }
        # process any chunks that arrived early
        for chunk in self.pending.get(fid, []):
            self._store_chunk(fid, chunk)
        self.pending.pop(fid, None)
        # update GUI: show incoming file placeholder
        self.gui.add_incoming_file_message(
            fid,
            self.incoming[fid]["name"],
            self.incoming[fid]["size"]
        )

    def _on_chunk(self, chunk):
        fid = chunk["file_id"]
        if fid not in self.incoming:
            # buffer until offer arrives
            self.pending.setdefault(fid, []).append(chunk)
            return
        self._store_chunk(fid, chunk)

    def _store_chunk(self, fid, chunk):
        """ Store a chunk of data in the incoming file entry.
            If the file is complete, notify the GUI.
        """
        entry = self.incoming[fid]
        idx = chunk["index"]
        data = base64.b64decode(chunk["data"].encode())
        if idx in entry["chunks"]:
            return  # duplicate
        entry["chunks"][idx] = data
        entry["received"] += len(data)
        # if complete, notify GUI
        if entry["received"] >= entry["size"]:
            entry["complete"] = True
            self.gui.enable_download(fid)

    def _on_cancel(self, cancel):
        fid = cancel.get("file_id")
        # clean up stored data
        if fid in self.incoming:
            del self.incoming[fid]
            self.gui.remove_file_message(fid)

