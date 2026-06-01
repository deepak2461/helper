# ============================================================
# UI / OVERLAY.PY
# Native desktop overlay window (tkinter)
# Features:
#   - Always on top, hidden from screen share + taskbar
#   - Closing hides window — app keeps running (system tray)
#   - Mode toggle (Auto / Manual)
#   - Manual mic start/stop button
#   - Screen capture button
#   - Direct ask input box
#   - Scrollable answer area with slim dark scrollbar
#   - Syncs mode with web/phone UI via queue
# ============================================================

import tkinter as tk
import ctypes
import threading
import webbrowser
import time
from logger import logger

# -------- Windows API Constants --------
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE            = -20
WS_EX_TOOLWINDOW       = 0x00000080
WS_EX_APPWINDOW        = 0x00040000


# -------- Get correct HWND --------
def get_hwnd(root):
    return ctypes.windll.user32.GetParent(root.winfo_id())


# -------- Hide from screen share --------
def hide_from_screenshare(hwnd):
    try:
        result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        logger.info("[UI] Screen share hidden" if result else "[UI] Screen share hide failed")
    except Exception as e:
        logger.error(f"[UI] Screen hide error: {e}")


# -------- Hide from taskbar + Alt-Tab --------
def hide_from_taskbar(hwnd):
    try:
        u = ctypes.windll.user32
        style = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
        u.SetWindowLongW(hwnd, GWL_EXSTYLE, (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW)
        u.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0023)
        logger.info("[UI] Taskbar hidden")
    except Exception as e:
        logger.error(f"[UI] Taskbar hide error: {e}")


# ============================================================
# MAIN OVERLAY FUNCTION
# ============================================================
def _run_overlay():
    from server import socket_server

    root = tk.Tk()
    root.title("HELPER")                          # no title text
    root.geometry("380x600")
    root.configure(bg="#0d0d14")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.96)         # opacity — change here
    root.resizable(True, True)
    root.overrideredirect(False)            # keep window chrome for dragging -- If set to True this removes the op bar check later , but close and other options such as dragging , min , max will be lost as well

    # -------- Apply hiding --------
    root.update()
    hwnd = get_hwnd(root)
    hide_from_screenshare(hwnd)
    hide_from_taskbar(hwnd)

    # -------- Closing hides window, does NOT kill app --------
    def on_close():
        logger.info("[UI] Window hidden — app still running")
        root.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # ================================================================
    # HEADER BAR
    # ================================================================
    header = tk.Frame(root, bg="#13131f", pady=0)
    header.pack(fill="x")

    # -------- Remove default tkinter white border by using custom header --------
    inner_header = tk.Frame(header, bg="#13131f", pady=8)
    inner_header.pack(fill="x", padx=12)

    tk.Label(inner_header, text="⚡ Helper",
             bg="#13131f", fg="#818cf8",
             font=("Segoe UI", 12, "bold")).pack(side="left")

    # -------- Globe icon — open browser (no button look) --------
    globe = tk.Label(inner_header, text="🌐",
                     bg="#13131f", fg="#334155",
                     font=("Segoe UI", 12), cursor="hand2")
    globe.pack(side="right")
    globe.bind("<Button-1>", lambda e: webbrowser.open("http://localhost:8000"))
    globe.bind("<Enter>", lambda e: globe.config(fg="#818cf8"))
    globe.bind("<Leave>", lambda e: globe.config(fg="#334155"))

    # Status dot
    status_dot = tk.Label(inner_header, text="●",
                          bg="#13131f", fg="#4ade80",
                          font=("Segoe UI", 9))
    status_dot.pack(side="right", padx=(0, 6))

    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    # ================================================================
    # MODE TOGGLE BAR
    # ================================================================
    mode_frame = tk.Frame(root, bg="#0d0d14", pady=7)
    mode_frame.pack(fill="x", padx=12)

    mode_label = tk.Label(mode_frame, text="🤖 Auto — always listening",
                          bg="#0d0d14", fg="#475569",
                          font=("Segoe UI", 9))
    mode_label.pack(side="left")

    is_manual    = [False]
    is_mic_active = [False]

    toggle_pill = tk.Label(mode_frame, text="AUTO",
                           bg="#1e293b", fg="#64748b",
                           font=("Segoe UI", 8, "bold"),
                           padx=8, pady=2, cursor="hand2")
    toggle_pill.pack(side="right")

    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    # ================================================================
    # MIC BUTTON FRAME (shown only in manual mode)
    # ================================================================
    mic_outer = tk.Frame(root, bg="#0d0d14")
    # not packed yet

    mic_btn = tk.Label(mic_outer, text="🎙️  Start Listening",
                       bg="#4f46e5", fg="white",
                       font=("Segoe UI", 10, "bold"),
                       pady=7, cursor="hand2", anchor="center")
    mic_btn.pack(fill="x", padx=12, pady=6)

    # ================================================================
    # ACTION ROW
    # ================================================================
    action_row = tk.Frame(root, bg="#0d0d14", pady=6)
    action_row.pack(fill="x", padx=12)

    # -------- Screen Capture Button --------
    capture_lbl = tk.Label(action_row, text="📸 Capture Screen",
                           bg="#1e293b", fg="#64748b",
                           font=("Segoe UI", 9),
                           padx=10, pady=4, cursor="hand2")
    capture_lbl.pack(side="left")

    # -------- Clear Button --------
    clear_lbl = tk.Label(action_row, text="✕ Clear",
                         bg="#0d0d14", fg="#334155",
                         font=("Segoe UI", 9),
                         padx=10, pady=4, cursor="hand2")
    clear_lbl.pack(side="right")

    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    # ================================================================
    # QUESTION LABEL
    # ================================================================
    question_frame = tk.Frame(root, bg="#13131f")
    # packed only when question arrives

    question_lbl = tk.Label(question_frame, text="",
                            bg="#13131f", fg="#818cf8",
                            font=("Segoe UI", 9, "italic"),
                            wraplength=340, justify="left",
                            anchor="w", padx=12, pady=5)
    question_lbl.pack(fill="x")

    # ================================================================
    # ANSWER AREA (scrollable, slim dark scrollbar)
    # ================================================================
    answer_outer = tk.Frame(root, bg="#0d0d14")
    answer_outer.pack(fill="both", expand=True, padx=12, pady=8)

    # -------- Custom slim scrollbar --------
    scrollbar = tk.Scrollbar(answer_outer, orient="vertical",
                             width=4,
                             troughcolor="#0d0d14",
                             bg="#1e293b",
                             activebackground="#334155",
                             relief="flat", bd=0)
    scrollbar.pack(side="right", fill="y")

    answer_text = tk.Text(answer_outer,
                          bg="#0d0d14", fg="#475569",
                          font=("Segoe UI", 11),
                          wrap="word", relief="flat",
                          padx=4, pady=4,
                          state="disabled", cursor="arrow",
                          selectbackground="#1e293b",
                          yscrollcommand=scrollbar.set,
                          insertbackground="#818cf8")
    answer_text.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=answer_text.yview)

    # Insert placeholder
    answer_text.config(state="normal")
    answer_text.insert(tk.END, "Waiting for question...")
    answer_text.config(state="disabled")

    # ================================================================
    # DIRECT ASK INPUT BOX
    # ================================================================
    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")

    ask_frame = tk.Frame(root, bg="#13131f", pady=6)
    ask_frame.pack(fill="x", padx=12)

    ask_entry = tk.Text(ask_frame, height=2,
                        bg="#1e293b", fg="#334155",
                        font=("Segoe UI", 10),
                        relief="flat", padx=8, pady=5,
                        wrap="word", insertbackground="#818cf8")
    ask_entry.pack(side="left", fill="x", expand=True)
    ask_entry.insert("1.0", "Ask anything...")

    def ask_focus_in(e):
        if ask_entry.get("1.0", tk.END).strip() == "Ask anything...":
            ask_entry.delete("1.0", tk.END)
            ask_entry.config(fg="#e2e8f0")

    def ask_focus_out(e):
        if not ask_entry.get("1.0", tk.END).strip():
            ask_entry.insert("1.0", "Ask anything...")
            ask_entry.config(fg="#334155")

    ask_entry.bind("<FocusIn>", ask_focus_in)
    ask_entry.bind("<FocusOut>", ask_focus_out)

    # -------- Send button --------
    send_btn = tk.Label(ask_frame, text="↑",
                        bg="#4f46e5", fg="white",
                        font=("Segoe UI", 13, "bold"),
                        padx=10, pady=5, cursor="hand2")
    send_btn.pack(side="right", padx=(6, 0))

    # ================================================================
    # STATUS BAR
    # ================================================================
    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")
    status_lbl = tk.Label(root, text="Ready",
                          bg="#0d0d14", fg="#334155",
                          font=("Segoe UI", 8),
                          anchor="w", padx=12)
    status_lbl.pack(fill="x", pady=3)

    # ================================================================
    # HELPER FUNCTIONS
    # ================================================================
    current_text = [""]

    def set_answer_text(text, color="#e2e8f0"):
        answer_text.config(state="normal")
        answer_text.delete("1.0", tk.END)
        if text:
            answer_text.insert(tk.END, text)
        answer_text.config(state="disabled", fg=color)
        answer_text.see(tk.END)

    def do_clear(e=None):
        current_text[0] = ""
        set_answer_text("Waiting for question...", color="#475569")
        question_lbl.config(text="")
        question_frame.pack_forget()
        status_lbl.config(text="Ready")

    def send_direct(e=None):
        text = ask_entry.get("1.0", tk.END).strip()
        if not text or text == "Ask anything...":
            return "break"
        ask_entry.delete("1.0", tk.END)
        ask_entry.config(fg="#334155")
        if socket_server.engine:
            status_lbl.config(text="💬 Asking...")
            threading.Thread(
                target=socket_server.engine.generate,
                args=(text,),
                daemon=True
            ).start()
        return "break"

    def do_capture(e=None):
        if socket_server.engine:
            status_lbl.config(text="📸 Capturing...")
            threading.Thread(
                target=socket_server.engine.generate_from_screen,
                daemon=True
            ).start()

    def toggle_mic(e=None):
        if not is_mic_active[0]:
            is_mic_active[0] = True
            mic_btn.config(text="⏹️  Stop Listening", bg="#dc2626")
            status_lbl.config(text="🎙️ Listening...")
            if socket_server.stt:
                socket_server.stt.start_manual()
        else:
            is_mic_active[0] = False
            mic_btn.config(text="🎙️  Start Listening", bg="#4f46e5")
            status_lbl.config(text="⏳ Processing...")
            if socket_server.stt:
                socket_server.stt.stop_manual()

    def toggle_mode(e=None):
        is_manual[0] = not is_manual[0]
        manual = is_manual[0]
        if manual:
            toggle_pill.config(text="MANUAL", bg="#4f46e5", fg="white")
            mode_label.config(text="🖐️ Manual — press button to listen")
            mic_outer.pack(fill="x", after=mode_frame)
        else:
            toggle_pill.config(text="AUTO", bg="#1e293b", fg="#64748b")
            mode_label.config(text="🤖 Auto — always listening")
            mic_outer.pack_forget()
            if is_mic_active[0]:
                toggle_mic()

        if socket_server.stt:
            socket_server.stt.set_mode(manual)

        # -------- Sync web + phone UI --------
        from server.socket_server import send_to_clients
        send_to_clients({"type": "mode_change", "manual": manual})

    # -------- Bind events --------
    toggle_pill.bind("<Button-1>", toggle_mode)
    mic_btn.bind("<Button-1>", toggle_mic)
    capture_lbl.bind("<Button-1>", do_capture)
    capture_lbl.bind("<Enter>", lambda e: capture_lbl.config(fg="white"))
    capture_lbl.bind("<Leave>", lambda e: capture_lbl.config(fg="#64748b"))
    clear_lbl.bind("<Button-1>", do_clear)
    clear_lbl.bind("<Enter>", lambda e: clear_lbl.config(fg="#64748b"))
    clear_lbl.bind("<Leave>", lambda e: clear_lbl.config(fg="#334155"))
    send_btn.bind("<Button-1>", send_direct)
    ask_entry.bind("<Return>", send_direct)

    # ================================================================
    # QUEUE POLLING — update UI from background threads
    # ================================================================
    def poll():
        try:
            while not socket_server.answer_queue.empty():
                msg_type, text = socket_server.answer_queue.get_nowait()

                if msg_type == "question":
                    current_text[0] = ""
                    question_lbl.config(text=f"❓ {text}")
                    question_frame.pack(fill="x", after=action_row)
                    set_answer_text("", color="#e2e8f0")
                    status_lbl.config(text="⏳ Generating...")

                elif msg_type == "chunk":
                    current_text[0] += text
                    set_answer_text(current_text[0])

                elif msg_type == "done":
                    status_lbl.config(text="✅ Ready")

                elif msg_type == "status":
                    status_lbl.config(text=text)

                elif msg_type == "mode":
                    # Web UI changed mode — sync tkinter toggle
                    new_manual = text  # text holds bool here
                    if new_manual != is_manual[0]:
                        toggle_mode()  # toggle to match

        except Exception as e:
            logger.error(f"[UI] Poll error: {e}")

        root.after(100, poll)

    poll()
    root.mainloop()


# -------- Launch in background thread --------
def launch_overlay():
    logger.info("[UI] Launching overlay...")
    threading.Thread(target=_run_overlay, daemon=True).start()