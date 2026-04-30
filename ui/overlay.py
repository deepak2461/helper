# ============================================================
# UI / OVERLAY.PY
# Native desktop overlay window using tkinter
# Features:
#   - Always on top
#   - Hidden from screen share (SetWindowDisplayAffinity)
#   - Hidden from taskbar and Alt-Tab
#   - Closing window does NOT kill the app (runs in thread)
#   - Mode toggle (Auto / Manual)
#   - Mic start/stop button (manual mode)
#   - Screen capture button
#   - Answer streams in real time via queue polling
# ============================================================

import tkinter as tk
from tkinter import font as tkfont
import ctypes
import threading
import webbrowser
import time
from logger import logger

# -------- Windows API Constants --------
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW  = 0x00040000


# -------- Get correct HWND for tkinter window --------
def get_hwnd(root):
    """Get the actual Windows handle for the tkinter window."""
    return ctypes.windll.user32.GetParent(root.winfo_id())


# -------- Hide Window from Screen Share --------
def hide_from_screenshare(hwnd):
    try:
        result = ctypes.windll.user32.SetWindowDisplayAffinity(
            hwnd, WDA_EXCLUDEFROMCAPTURE
        )
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
        # Force taskbar to refresh
        root_hwnd = ctypes.windll.user32.GetDesktopWindow()
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0023)
        logger.info("[UI] Window hidden from taskbar")
    except Exception as e:
        logger.error(f"[UI] Taskbar hide error: {e}")


# -------- Build and Run the Tkinter Window --------
def _run_overlay():
    from server import socket_server
    
    # -------- Start system tray --------
    from ui.tray import start_tray
    overlay_root_ref = [None]
    start_tray(overlay_root_ref)

    root = tk.Tk()
    overlay_root_ref[0] = root
    root.title("Helper")
    root.geometry("380x580")
    root.configure(bg="#0d0d14")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.70)    # ← [ Opacity ] Range: 0.0 (invisible) to 1.0 (solid)
    root.resizable(True, True)

    # -------- Apply Windows hiding after window is drawn --------
    root.update()
    hwnd = get_hwnd(root)
    hide_from_screenshare(hwnd)
    hide_from_taskbar(hwnd)

    # -------- Closing window hides it, does NOT kill app --------
    def on_close():
        logger.info("[UI] Overlay hidden — still running. Check system tray.")
        root.withdraw()  # hide instead of destroy

    root.protocol("WM_DELETE_WINDOW", on_close)

    # ================================================================
    # HEADER BAR
    # ================================================================
    header = tk.Frame(root, bg="#13131f", pady=10)
    header.pack(fill="x", padx=0)

    tk.Label(
        header, text="⚡ Helper",
        bg="#13131f", fg="#818cf8",
        font=("Segoe UI", 13, "bold")
    ).pack(side="left", padx=14)

    # -------- Globe icon — open browser (no button look) --------
    globe_label = tk.Label(
        header, text="🌐",
        bg="#13131f", fg="#475569",
        font=("Segoe UI", 13),
        cursor="hand2"
    )
    globe_label.pack(side="right", padx=14)
    globe_label.bind("<Button-1>", lambda e: webbrowser.open("http://localhost:8000"))
    globe_label.bind("<Enter>", lambda e: globe_label.config(fg="#94a3b8"))
    globe_label.bind("<Leave>", lambda e: globe_label.config(fg="#475569"))

    # Status dot
    status_dot = tk.Label(
        header, text="●",
        bg="#13131f", fg="#4ade80",
        font=("Segoe UI", 10)
    )
    status_dot.pack(side="right", padx=(0, 4))

    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    # ================================================================
    # MODE TOGGLE BAR (Auto / Manual)
    # ================================================================
    mode_frame = tk.Frame(root, bg="#0d0d14", pady=8)
    mode_frame.pack(fill="x", padx=14)

    mode_label = tk.Label(
        mode_frame, text="🤖 Auto — always listening",
        bg="#0d0d14", fg="#64748b",
        font=("Segoe UI", 9)
    )
    mode_label.pack(side="left")

    is_manual = [False]

    # -------- Simple toggle button (styled as pill) --------
    toggle_btn = tk.Label(
        mode_frame, text="AUTO",
        bg="#1e293b", fg="#94a3b8",
        font=("Segoe UI", 8, "bold"),
        padx=8, pady=3,
        cursor="hand2",
        relief="flat"
    )
    toggle_btn.pack(side="right")

    def toggle_mode(e=None):
        is_manual[0] = not is_manual[0]
        if is_manual[0]:
            toggle_btn.config(text="MANUAL", bg="#4f46e5", fg="white")
            mode_label.config(text="🖐️ Manual — press button to listen")
            mic_frame.pack(fill="x", padx=14, pady=(0, 6) , before=action_frame)
        else:
            toggle_btn.config(text="AUTO", bg="#1e293b", fg="#94a3b8")
            mode_label.config(text="🤖 Auto — always listening")
            mic_frame.pack_forget()
            # reset mic if active
            if is_mic_active[0]:
                toggle_mic()

        if socket_server.stt:
            socket_server.stt.set_mode(is_manual[0])
            # -------- Sync web UI toggle --------
            from server.socket_server import send_to_clients
            send_to_clients({"type": "mode_change", "manual": is_manual[0]})

    toggle_btn.bind("<Button-1>", toggle_mode)

    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    # ================================================================
    # MIC BUTTON (Manual mode only — hidden by default)
    # ================================================================
    mic_frame = tk.Frame(root, bg="#0d0d14")
    # not packed yet — shown only in manual mode

    is_mic_active = [False]

    mic_btn = tk.Label(
        mic_frame, text="🎙️  Start Listening",
        bg="#4f46e5", fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=12, pady=7,
        cursor="hand2",
        anchor="center"
    )
    mic_btn.pack(fill="x")

    def toggle_mic(e=None):
        if not is_mic_active[0]:
            is_mic_active[0] = True
            mic_btn.config(text="⏹️  Stop Listening", bg="#dc2626")
            status_label.config(text="🎙️ Listening...")
            if socket_server.stt:
                socket_server.stt.start_manual()
        else:
            is_mic_active[0] = False
            mic_btn.config(text="🎙️  Start Listening", bg="#4f46e5")
            status_label.config(text="⏳ Processing...")
            if socket_server.stt:
                socket_server.stt.stop_manual()

    mic_btn.bind("<Button-1>", toggle_mic)

    # ================================================================
    # ACTION ROW (Capture Screen)
    # ================================================================
    action_frame = tk.Frame(root, bg="#0d0d14", pady=8)
    action_frame.pack(fill="x", padx=14)

    # -------- Screen Capture Button --------
    def do_capture(e=None):
        if socket_server.engine:
            status_label.config(text="📸 Capturing screen...")
            threading.Thread(
                target=socket_server.engine.generate_from_screen,
                daemon=True
            ).start()
        else:
            status_label.config(text="❌ Engine not ready")

    capture_btn = tk.Label(
        action_frame,
        text="📸  Capture Screen",
        bg="#1e293b", fg="#94a3b8",
        font=("Segoe UI", 9),
        padx=10, pady=5,
        cursor="hand2"
    )
    capture_btn.pack(side="left")
    capture_btn.bind("<Button-1>", do_capture)
    capture_btn.bind("<Enter>", lambda e: capture_btn.config(fg="white"))
    capture_btn.bind("<Leave>", lambda e: capture_btn.config(fg="#94a3b8"))

    # -------- Clear Button --------
    def do_clear(e=None):
        current_text[0] = ""
        answer_text.config(state="normal")
        answer_text.delete("1.0", tk.END)
        answer_text.insert(tk.END, "Waiting for question...")
        answer_text.config(state="disabled", fg="#475569")
        question_label.config(text="")
        question_frame.pack_forget()
        status_label.config(text="Ready")

    clear_btn = tk.Label(
        action_frame,
        text="✕ Clear",
        bg="#0d0d14", fg="#334155",
        font=("Segoe UI", 9),
        padx=10, pady=5,
        cursor="hand2"
    )
    clear_btn.pack(side="right")
    clear_btn.bind("<Button-1>", do_clear)
    clear_btn.bind("<Enter>", lambda e: clear_btn.config(fg="#64748b"))
    clear_btn.bind("<Leave>", lambda e: clear_btn.config(fg="#334155"))

    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    # ================================================================
    # QUESTION DISPLAY
    # ================================================================
    question_frame = tk.Frame(root, bg="#13131f", pady=0)
    # packed only when question arrives

    question_label = tk.Label(
        question_frame,
        text="",
        bg="#13131f", fg="#818cf8",
        font=("Segoe UI", 9, "italic"),
        wraplength=340,
        justify="left",
        anchor="w",
        padx=14, pady=6
    )
    question_label.pack(fill="x")
    
    # ================================================================
    # ANSWER DISPLAY (scrollable text area)
    # ================================================================
    answer_frame = tk.Frame(root, bg="#0d0d14")
    answer_frame.pack(fill="both", expand=True, padx=14, pady=10)
    '''
    answer_text = tk.Text(
        answer_frame,
        bg="#0d0d14", fg="#475569",
        font=("Segoe UI", 11),
        wrap="word",
        relief="flat",
        padx=4, pady=4,
        state="disabled",
        cursor="arrow",
        selectbackground="#1e293b"
    )
    answer_text.pack(fill="both", expand=True)

    # insert placeholder
    answer_text.config(state="normal")
    answer_text.insert(tk.END, "Waiting for question...")
    answer_text.config(state="disabled")
    '''

    # -------- Answer Display with Scrollbar --------
    answer_scroll = tk.Scrollbar(answer_frame)
    answer_scroll.pack(side="right", fill="y")

    answer_text = tk.Text(
        answer_frame,
        bg="#0d0d14", fg="#475569",
        font=("Segoe UI", 11),
        wrap="word", relief="flat",
        padx=4, pady=4,
        state="disabled", cursor="arrow",
        selectbackground="#1e293b",
        yscrollcommand=answer_scroll.set
    )
    answer_text.pack(fill="both", expand=True)
    answer_scroll.config(command=answer_text.yview)


    # ================================================================
    # DIRECT ASK INPUT BOX
    # ================================================================
    ask_frame = tk.Frame(root, bg="#0d0d14", pady=6)
    ask_frame.pack(fill="x", padx=14)

    ask_entry = tk.Text(
        ask_frame, height=2,
        bg="#13131f", fg="#e2e8f0",
        font=("Segoe UI", 10),
        relief="flat", padx=8, pady=6,
        wrap="word", insertbackground="#818cf8"
    )
    ask_entry.pack(side="left", fill="x", expand=True)
    ask_entry.insert("1.0", "Ask anything...")
    ask_entry.config(fg="#334155")

    # -------- Placeholder behaviour --------
    def on_ask_focus_in(e):
        if ask_entry.get("1.0", tk.END).strip() == "Ask anything...":
            ask_entry.delete("1.0", tk.END)
            ask_entry.config(fg="#e2e8f0")

    def on_ask_focus_out(e):
        if not ask_entry.get("1.0", tk.END).strip():
            ask_entry.insert("1.0", "Ask anything...")
            ask_entry.config(fg="#334155")

    ask_entry.bind("<FocusIn>", on_ask_focus_in)
    ask_entry.bind("<FocusOut>", on_ask_focus_out)

    # -------- Send on Enter --------
    def send_direct(e=None):
        text = ask_entry.get("1.0", tk.END).strip()
        if not text or text == "Ask anything...":
            return "break"
        ask_entry.delete("1.0", tk.END)
        if socket_server.engine:
            status_label.config(text="💬 Asking...")
            threading.Thread(
                target=socket_server.engine.generate,
                args=(text,),
                daemon=True
            ).start()
        return "break"  # prevents newline on Enter

    ask_btn = tk.Label(
        ask_frame, text="↑",
        bg="#4f46e5", fg="white",
        font=("Segoe UI", 12, "bold"),
        padx=10, pady=6,
        cursor="hand2"
    )
    ask_btn.pack(side="right", padx=(6, 0))
    ask_btn.bind("<Button-1>", send_direct)
    ask_entry.bind("<Return>", send_direct)


    # ================================================================
    # STATUS BAR
    # ================================================================
    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")
    status_label = tk.Label(
        root, text="Ready",
        bg="#0d0d14", fg="#334155",
        font=("Segoe UI", 8),
        anchor="w", padx=14
    )
    status_label.pack(fill="x", pady=4)

    # ================================================================
    # QUEUE POLLING — Update UI from background threads
    # ================================================================
    current_text = [""]

    def poll_answer():
        try:
            while not socket_server.answer_queue.empty():
                msg_type, text = socket_server.answer_queue.get_nowait()

                # -------- Question arrived --------
                if msg_type == "question":
                    current_text[0] = ""
                    question_label.config(text=f"❓ {text}")
                    question_frame.pack(fill="x", after=action_frame)
                    answer_text.config(state="normal")
                    answer_text.delete("1.0", tk.END)
                    answer_text.config(fg="#e2e8f0", state="disabled")
                    status_label.config(text="⏳ Generating...")

                # -------- Answer chunk streaming --------
                elif msg_type == "chunk":
                    current_text[0] += text
                    answer_text.config(state="normal")
                    answer_text.delete("1.0", tk.END)
                    answer_text.insert(tk.END, current_text[0])
                    answer_text.see(tk.END)
                    answer_text.config(state="disabled")

                # -------- Answer complete --------
                elif msg_type == "done":
                    status_label.config(text="✅ Ready")

                # -------- Status update --------
                elif msg_type == "status":
                    status_label.config(text=text)

        except Exception as e:
            logger.error(f"[UI] Poll error: {e}")

        root.after(100, poll_answer)

    poll_answer()
    root.mainloop()


# -------- Launch Overlay in Background Thread --------
def launch_overlay():
    """
    Runs the tkinter window in its own thread.
    Closing the window hides it — does NOT kill the app.
    App continues running for phone UI access.
    """
    logger.info("[UI] Launching overlay in background thread...")
    thread = threading.Thread(target=_run_overlay, daemon=True)
    thread.start()