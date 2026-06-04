# ============================================================
# MAIN.PY
# Entry point — starts all services and launches overlay
# ============================================================

import socket
import time
import threading
import os
from dotenv import load_dotenv
from logger import logger
from audio.mic_stream import start_mic_stream
from stt.deepgram_client import DeepgramSTT
from utils.context_loader import load_context
from llm.answer_engine import AnswerEngine
from server.socket_server import start_server_thread
from ui.overlay import launch_overlay


# -------- Get Local IP for Phone Access --------
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


# -------- STT Thread --------
def run_stt(stt, audio_stream):
    stt.run(audio_stream)


def main():
    load_dotenv()
    logger.info("[MAIN] Starting Helper...")

    # -------- Start WebSocket Server --------
    start_server_thread()
    time.sleep(1)

    local_ip = get_local_ip()
    print(f"\n{'='*45}")
    print(f"  ✅ Desktop UI : http://localhost:8000")
    print(f"  📱 Phone UI   : http://{local_ip}:8000")
    print(f"{'='*45}\n")

    # -------- Load Resume + JD --------
    context = load_context(resume_path="docs/resume.pdf", jd_path="docs/jd.pdf")

    # -------- Init LLM Engine --------
    engine = AnswerEngine(resume=context["resume"], jd=context["jd"])

    # -------- Init STT --------
    stt = DeepgramSTT(answer_engine=engine)

    # -------- Expose STT controls to WebSocket --------
    # Import here to avoid circular import
    from server import socket_server
    socket_server.stt = stt
    socket_server.engine = engine

    # -------- Start Mic + STT in Background Thread --------
    # audio_stream = start_mic_stream()
    # stt_thread = threading.Thread(target=run_stt, args=(stt, audio_stream), daemon=True)
    # stt_thread.start()

    # -------- Audio mode selection --------
    # Use AUDIO_MODE=mic or AUDIO_MODE=loopback in .env. Default keeps the previous behavior.
    audio_mode = os.getenv("AUDIO_MODE", "loopback").strip().lower()
    if audio_mode not in ("mic", "loopback"):
        logger.warning(f"[MAIN] Invalid AUDIO_MODE '{audio_mode}', falling back to loopback")
        audio_mode = "loopback"
    logger.info(f"[MAIN] Audio mode: {audio_mode}")

    from audio.mic_stream import start_audio_stream
    audio_stream = start_audio_stream(mode=audio_mode) 

    stt_thread = threading.Thread(target=run_stt, args=(stt, audio_stream), daemon=True)
    stt_thread.start()  

    # -------- Launch Desktop Overlay (non-blocking) --------
    launch_overlay()

    # -------- Keep main thread alive --------
    logger.info("[MAIN] App running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("[MAIN] Shutting down...")


if __name__ == "__main__":
    main()






'''
from audio.mic_stream import start_mic_stream
from logger import logger
from stt.deepgram_client import DeepgramSTT
from utils.context_loader import load_context
from llm.answer_engine import AnswerEngine
from dotenv import load_dotenv

def main():
    load_dotenv()
    logger.info("Starting Helper...")

    ## Added below 5 lines while trying to capture system audio, but it is not working yet. Will debug later. [  29/04/26 - 12:20 AM ]
    # print("\nAudio mode:")
    # print("  [1] Microphone (default) — captures your voice + nearby sounds")
    # print("  [2] System audio loopback — captures YouTube, Meet, Zoom etc.")
    # choice = input("\nChoose mode (1 or 2): ").strip()
    # loopback = choice == "2"

    # Load resume + JD
    context = load_context(resume_path="docs/resume.pdf", jd_path="docs/jd.pdf")

    # Init LLM engine
    engine = AnswerEngine(resume=context["resume"], jd=context["jd"])

    # Init STT
    stt = DeepgramSTT(answer_engine=engine)

    # Start mic + run
    audio_stream = start_mic_stream()
    stt.run(audio_stream)


if __name__ == "__main__":
    main()


    

'''
