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

import pystray
from PIL import Image

# -------- Windows API Constants --------
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE            = -20
WS_EX_TOOLWINDOW       = 0x00000080
WS_EX_APPWINDOW        = 0x00040000
ACCENT_COLOR           = "#818cf8"
IDLE_WARNING_AFTER     = 10
IDLE_WARNING_SECONDS   = 10


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

    # ------------------------------------------------
    # System Tray
    # ------------------------------------------------

    def show_window(icon=None, item=None):
        logger.info("[TRAY] Restoring window")

        root.after(0, root.deiconify)
        root.after(0, root.lift)
        root.after(0, lambda: root.attributes("-topmost", True))

    def exit_app(icon=None, item=None):
        logger.info("[TRAY] Exiting application")

        try:
            tray_icon.stop()
        except:
            pass

        root.after(0, root.destroy)

    # Temporary blue icon
    tray_image = Image.new("RGB", (64, 64), (51, 70, 242))

    try:
        tray_icon = pystray.Icon(
            "helper",
            tray_image,
            "Helper",
            menu=pystray.Menu(
                pystray.MenuItem("Open", show_window),
                pystray.MenuItem("Exit", exit_app),
            ),
        )
        tray_icon.visible = True    # Make tray icon open window on double-click

        threading.Thread(
            target=tray_icon.run,
            daemon=True
        ).start()
        logger.info("[TRAY] Tray started")
    except Exception as e:
        logger.exception(f"[TRAY] Tray Failed: {e}")


    # ================================================================
    # HEADER BAR
    # ================================================================
    header = tk.Frame(root, bg="#13131f", pady=0)
    header.pack(fill="x")

    # -------- Remove default tkinter white border by using custom header --------
    inner_header = tk.Frame(header, bg="#13131f", pady=8)
    inner_header.pack(fill="x", padx=12)

    tk.Label(inner_header, text="⚡ Helper",
             bg="#13131f", fg=ACCENT_COLOR,
             font=("Segoe UI", 12, "bold")).pack(side="left")

    # -------- Globe icon — open browser (no button look) --------
    globe = tk.Label(inner_header, text="🌐",
                     bg="#13131f", fg="#334155",
                     font=("Segoe UI", 12), cursor="hand2")
    globe.pack(side="right")
    globe.bind("<Button-1>", lambda e: webbrowser.open("http://localhost:8000"))
    globe.bind("<Enter>", lambda e: globe.config(fg=ACCENT_COLOR))
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
    capture_lbl.pack(side="left", padx=(0, 6))

    # -------- Timeout Timer Button (hidden initially, appears in header after idle warning) --------
    timeout_timer = tk.Label(inner_header, text="⏱️ 10s",
                             bg="#13131f", fg=ACCENT_COLOR,
                             font=("Segoe UI", 8, "bold"),
                             padx=6, pady=1, cursor="hand2")
    # Timer starts hidden, shown by poll() after idle warning threshold

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
                            bg="#13131f", fg=ACCENT_COLOR,
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
                          insertbackground=ACCENT_COLOR)
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

    ask_frame = tk.Frame(root, bg="#13131f", pady=8, padx=12)
    # Don't reference `status_lbl` here — it is defined later in the function.
    ask_frame.pack(fill="x", after=action_row)

    ask_entry = tk.Text(ask_frame, height=2,
                        bg="#1e293b", fg="#334155",
                        font=("Segoe UI", 10),
                        relief="solid", bd=1, borderwidth=1, padx=8, pady=6,
                        wrap="word", insertbackground=ACCENT_COLOR)
    ask_entry.pack(side="left", fill="both", expand=True, padx=(0, 6))
    ask_placeholder = ["Ask anything...", True]

    def set_ask_placeholder():
        ask_placeholder[1] = True
        ask_entry.delete("1.0", tk.END)
        ask_entry.insert("1.0", ask_placeholder[0])
        ask_entry.config(fg="#64748b")

    def clear_ask_placeholder():
        if ask_placeholder[1]:
            ask_placeholder[1] = False
            ask_entry.delete("1.0", tk.END)
            ask_entry.config(fg="#e2e8f0")

    set_ask_placeholder()

    def ask_focus_in(e):
        clear_ask_placeholder()

    def ask_focus_out(e):
        if not ask_entry.get("1.0", tk.END).strip():
            set_ask_placeholder()

    def ask_key_press(e):
        clear_ask_placeholder()

    ask_entry.bind("<FocusIn>", ask_focus_in)
    ask_entry.bind("<FocusOut>", ask_focus_out)
    ask_entry.bind("<KeyPress>", ask_key_press, add="+")

    # -------- Send button --------
    send_btn = tk.Label(ask_frame, text="↑",
                        bg="#4f46e5", fg="white",
                        font=("Segoe UI", 13, "bold"),
                        padx=10, pady=6, cursor="hand2", 
                        relief="solid", bd=0) 
    send_btn.pack(side="right", fill="y")
    # Ensure input frame and send button are above the answer area
    try:
        ask_frame.lift()
        send_btn.lift()
    except Exception:
        pass

    # ================================================================
    # STATUS BAR
    # ================================================================
    tk.Frame(root, bg="#1e1e2e", height=1).pack(fill="x")
    status_lbl = tk.Label(root, text="Ready",
                          bg="#0d0d14", fg="#334155",
                          font=("Segoe UI", 8),
                          anchor="w", padx=12)
    status_lbl.pack(fill="x", pady=3, side="bottom")

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
        clear_ask_placeholder()
        text = ask_entry.get("1.0", tk.END).strip()
        if text.startswith(ask_placeholder[0]):
            text = text[len(ask_placeholder[0]):].strip()

        if not text:
            status_lbl.config(text="⚠️ Empty question")
            set_ask_placeholder()
            return "break"
        
        logger.info(f"[UI] Direct ask: {text}")
        set_ask_placeholder()
        
        if socket_server.engine:
            # Show question in UI
            current_text[0] = ""
            question_lbl.config(text=f"❓ {text}")
            question_frame.pack(fill="x", after=ask_frame)
            set_answer_text("", color="#e2e8f0")
            
            status_lbl.config(text="💬 Asking...")
            send_btn.config(bg="#666666")  # Visual feedback - disable button appearance
            
            def process_question():
                try:
                    socket_server.engine.generate(text)
                except Exception as ex:
                    logger.error(f"[UI] Error sending question: {ex}")
                    status_lbl.config(text=f"❌ Error: {str(ex)[:50]}")
                finally:
                    send_btn.config(bg="#4f46e5")  # Re-enable button
            
            threading.Thread(target=process_question, daemon=True).start()
        else:
            status_lbl.config(text="❌ Engine not ready")
            logger.warning("[UI] socket_server.engine not initialized")
        
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

    # -------- Timer button interaction --------
    def show_reconnect_button():
        timer_state["shown"] = True
        timer_state["expired"] = True
        timeout_timer.config(text="🔄", fg=ACCENT_COLOR, cursor="hand2")
        if not timeout_timer.winfo_ismapped():
            timeout_timer.pack(side="right", padx=(0, 8), before=status_dot)

    def reset_idle_timer(show_sync=True):
        if not timer_state["connected"]:
            return

        timer_state["start_time"] = time.time()
        timer_state["shown"] = False
        timer_state["expired"] = False
        timeout_timer.pack_forget()

        if show_sync:
            # Notify server to sync reset across all clients
            from server.socket_server import send_to_clients
            send_to_clients({"type": "timer_reset"})

    def reset_timeout_timer(e=None):
        """User clicked the header timer/reconnect control."""
        if not timer_state["connected"]:
            logger.info("[UI] STT reconnect requested")
            timer_state["reconnecting"] = True
            timeout_timer.config(text="🔄")
            status_lbl.config(text="Reconnecting Deepgram...")
            if socket_server.stt:
                socket_server.stt.reconnect()
            return

        logger.info("[UI] Timer reset requested")
        if socket_server.stt:
            socket_server.stt.extend_timeout()
        reset_idle_timer(show_sync=True)

    timeout_timer.bind("<Button-1>", reset_timeout_timer)
    timeout_timer.bind("<Enter>", lambda e: timeout_timer.config(fg="#a5b4fc"))
    timeout_timer.bind("<Leave>", lambda e: timeout_timer.config(fg=ACCENT_COLOR))

    # ================================================================
    # QUEUE POLLING — update UI from background threads
    # ================================================================
    
    # Timer state tracking
    timer_state = {
        "start_time": time.time(),
        "shown": False,
        "expired": False,
        "connected": True,
        "reconnecting": False,
    }

    def poll():
        try:
            while not socket_server.answer_queue.empty():
                msg_type, text = socket_server.answer_queue.get_nowait()

                if msg_type == "question":
                    reset_idle_timer(show_sync=False)
                    current_text[0] = ""
                    question_lbl.config(text=f"❓ {text}")
                    question_frame.pack(fill="x", after=ask_frame)
                    set_answer_text("", color="#e2e8f0")
                    status_lbl.config(text="⏳ Generating...")

                elif msg_type == "chunk":
                    current_text[0] += text
                    set_answer_text(current_text[0])

                elif msg_type == "done":
                    reset_idle_timer(show_sync=False)
                    status_lbl.config(text="✅ Ready")

                elif msg_type == "status":
                    if "Listening" in text or "Processing" in text:
                        reset_idle_timer(show_sync=False)
                    status_lbl.config(text=text)

                elif msg_type in ("speech_activity", "timer_reset"):
                    reset_idle_timer(show_sync=False)

                elif msg_type == "stt_disconnected":
                    timer_state["connected"] = False
                    timer_state["reconnecting"] = False
                    status_dot.config(fg="#ef4444")
                    status_lbl.config(text="Deepgram disconnected")
                    show_reconnect_button()

                elif msg_type == "stt_reconnecting":
                    timer_state["connected"] = False
                    timer_state["reconnecting"] = True
                    status_dot.config(fg="#f59e0b")
                    status_lbl.config(text="Reconnecting Deepgram...")
                    show_reconnect_button()

                elif msg_type == "stt_connected":
                    timer_state["connected"] = True
                    timer_state["reconnecting"] = False
                    status_dot.config(fg="#4ade80")
                    status_lbl.config(text="Deepgram connected")
                    reset_idle_timer(show_sync=False)

                elif msg_type == "mode":
                    # Web UI changed mode — sync tkinter toggle
                    new_manual = text  # text holds bool here
                    if new_manual != is_manual[0]:
                        toggle_mode()  # toggle to match

        except Exception as e:
            logger.error(f"[UI] Poll error: {e}")

        # -------- Timer countdown logic --------
        # Hidden for 10s of inactivity, then shows a 10s warning countdown.
        if not timer_state["connected"]:
            root.after(100, poll)
            return

        elapsed = time.time() - timer_state["start_time"]
        
        if (not timer_state["expired"]
                and elapsed >= IDLE_WARNING_AFTER
                and not timer_state["shown"]):
            timer_state["shown"] = True
            timeout_timer.pack(side="right", padx=(0, 8), before=status_dot)
            logger.debug("[UI] Timer button shown")
        
        if timer_state["shown"] and not timer_state["expired"]:
            warning_elapsed = int(elapsed - IDLE_WARNING_AFTER)
            remaining = max(0, IDLE_WARNING_SECONDS - warning_elapsed)
            timeout_timer.config(text=f"⏱️ {remaining}s")
            
            if remaining == 0:
                # Timeout occurred - leave underlying Deepgram/app behavior alone.
                logger.warning("[UI] Timeout countdown reached 0")
                timeout_timer.pack_forget()
                timer_state["shown"] = False
                timer_state["expired"] = True

        root.after(100, poll)

    poll()
    root.mainloop()


# -------- Launch in background thread --------
def launch_overlay():
    logger.info("[UI] Launching overlay...")
    threading.Thread(target=_run_overlay, daemon=True).start()
