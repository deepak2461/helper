# ============================================================
# UI / OVERLAY.PY
# Native desktop window using tkinter + webbrowser
# Hidden from screen share via Windows SetWindowDisplayAffinity
# Always on top, movable, resizable
# tkinter is built into Python — no install needed
# ============================================================

import tkinter as tk
import ctypes
import threading
import webbrowser
import time
from logger import logger

# -------- Windows API Constants --------
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000


# -------- Hide Window from Screen Share --------
def hide_from_screenshare(hwnd):
    try:
        user32 = ctypes.windll.user32
        result = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        if result:
            logger.info("[UI] Window hidden from screen share")
        else:
            logger.warning("[UI] Failed to hide from screen share")
    except Exception as e:
        logger.error(f"[UI] Screen hide error: {e}")


# -------- Hide Window from Taskbar and Alt-Tab --------
def hide_from_taskbar(hwnd):
    try:
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        logger.info("[UI] Window hidden from taskbar")
    except Exception as e:
        logger.error(f"[UI] Taskbar hide error: {e}")


# -------- Launch Overlay Window --------
def launch_overlay():
    """
    Opens a native tkinter window with embedded browser frame.
    Always on top, movable, resizable, hidden from screen share.
    """
    logger.info("[UI] Launching overlay window...")

    # Give server a moment to be ready
    time.sleep(1)

    root = tk.Tk()
    root.title("Helper")
    root.geometry("420x600")
    root.configure(bg="#0a0a0f")
    root.attributes("-topmost", True)       # always on top
    root.attributes("-alpha", 0.97)         # slight transparency
    root.resizable(True, True)              # resizable

    # -------- Get Windows HWND for API calls --------
    root.update()
    hwnd = ctypes.windll.user32.GetForegroundWindow()

    # -------- Apply Screen Share + Taskbar Hiding --------
    hide_from_screenshare(hwnd)
    hide_from_taskbar(hwnd)

    # -------- Fallback UI inside tkinter --------
    # Since we can't embed a browser easily without pywebview,
    # we open the browser separately and show a minimal control panel here

    # -------- Header --------
    header = tk.Frame(root, bg="#0a0a0f", pady=8)
    header.pack(fill="x", padx=14)

    tk.Label(
        header, text="⚡ Helper",
        bg="#0a0a0f", fg="#a5b4fc",
        font=("Segoe UI", 13, "bold")
    ).pack(side="left")

    tk.Label(
        header, text="🟢 Running",
        bg="#0a0a0f", fg="#4ade80",
        font=("Segoe UI", 10)
    ).pack(side="right")

    # -------- Divider --------
    tk.Frame(root, bg="#1e293b", height=1).pack(fill="x")

    # -------- Open Browser Button --------
    btn_frame = tk.Frame(root, bg="#0a0a0f", pady=10)
    btn_frame.pack(fill="x", padx=14)

    def open_browser():
        webbrowser.open("http://localhost:8000")

    tk.Button(
        btn_frame,
        text="🌐 Open Full UI in Browser",
        command=open_browser,
        bg="#4f46e5", fg="white",
        font=("Segoe UI", 10),
        relief="flat", cursor="hand2",
        pady=6
    ).pack(fill="x")

    # -------- Answer Display Area --------
    tk.Frame(root, bg="#1e293b", height=1).pack(fill="x", pady=(10, 0))

    answer_label = tk.Label(
        root, text="Answer will appear here...",
        bg="#0a0a0f", fg="#e2e8f0",
        font=("Segoe UI", 11),
        wraplength=380,
        justify="left",
        anchor="nw",
        padx=14, pady=14
    )
    answer_label.pack(fill="both", expand=True)

    # -------- Update answer from WebSocket events --------
    # Poll a shared queue to update the label
    from server import socket_server

    current_text = [""]

    def poll_answer():
        try:
            while not socket_server.answer_queue.empty():
                msg_type, text = socket_server.answer_queue.get_nowait()

                if msg_type == "question":
                    current_text[0] = ""
                    answer_label.config(fg="#a5b4fc")  # blue for question incoming
                    status_label.config(text="⏳ Generating answer...")

                elif msg_type == "chunk":
                    current_text[0] += text
                    answer_label.config(
                        text=current_text[0],
                        fg="#e2e8f0"
                    )

                elif msg_type == "done":
                    status_label.config(text="✅ Ready")

        except Exception as e:
            pass
        root.after(100, poll_answer)  # check every 100ms
        
    # -------- Status Bar --------
    tk.Frame(root, bg="#1e293b", height=1).pack(fill="x")
    status_label = tk.Label(
        root, text="Ready",
        bg="#0a0a0f", fg="#475569",
        font=("Segoe UI", 9),
        anchor="w", padx=14
    )
    status_label.pack(fill="x", pady=4)

    poll_answer()
    root.mainloop()